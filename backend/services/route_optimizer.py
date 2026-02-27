"""
Daladan Platform — Route Optimizer Service
Implements the Greedy Pooling Algorithm with Haversine distance math
and PostGIS spatial queries for finding nearby cargo.
"""
import math
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import WKTElement
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_X, ST_Y

from backend.models import MarketNeed
from backend.schemas.routing import (
    NearbyCargoItem,
    OptimizedWaypoint,
    OptimizeRouteRequest,
    OptimizeRouteResponse,
    GreedyStepExplanation,
)

logger = logging.getLogger("daladan.routing")

# ── Constants ──
EARTH_RADIUS_KM = 6371.0
AVG_SPEED_KMH = 40.0  # average truck speed on Uzbek roads
CO2_PER_KM_SAVED = 0.6  # kg CO₂ saved per km by pooling vs separate trip
MIN_DETOUR_KM = 0.5  # minimum detour distance to avoid division-by-zero


class RouteOptimizer:
    """
    Location Optimization Engine.

    Accepts a driver's current position, destination, and remaining capacity.
    Uses PostGIS to find nearby cargo and a greedy knapsack algorithm
    to select the most profitable micro-detours.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ═══════════════════════════════════════════════════
    #  Haversine Distance
    # ═══════════════════════════════════════════════════

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two GPS points.

        Returns distance in **kilometers**.
        Uses the Haversine formula.
        """
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_KM * c

    # ═══════════════════════════════════════════════════
    #  Point-to-Line-Segment Distance
    # ═══════════════════════════════════════════════════

    @classmethod
    def point_to_segment_distance(
        cls,
        px: float, py: float,
        ax: float, ay: float,
        bx: float, by: float,
    ) -> float:
        """
        Approximate the perpendicular distance from a point (px, py) to
        the line segment (ax, ay) → (bx, by) in km.

        Uses projected coordinates for the closest-point calculation,
        then Haversine for the actual distance.
        """
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            # Segment is a point
            return cls.haversine(py, px, ay, ax)

        # Parameter t of the projection onto the line (0..1 = on segment)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        closest_x = ax + t * dx
        closest_y = ay + t * dy

        return cls.haversine(py, px, closest_y, closest_x)

    # ═══════════════════════════════════════════════════
    #  Detour Distance Calculation
    # ═══════════════════════════════════════════════════

    @classmethod
    def calculate_detour(
        cls,
        pickup_lat: float, pickup_lng: float,
        current_lat: float, current_lng: float,
        dest_lat: float, dest_lng: float,
    ) -> float:
        """
        Calculate the extra distance incurred by detouring through a pickup point.

        Detour = (current → pickup) + (pickup → dest) - (current → dest)
        """
        direct = cls.haversine(current_lat, current_lng, dest_lat, dest_lng)
        via_pickup = (
            cls.haversine(current_lat, current_lng, pickup_lat, pickup_lng)
            + cls.haversine(pickup_lat, pickup_lng, dest_lat, dest_lng)
        )
        detour = via_pickup - direct
        return max(detour, MIN_DETOUR_KM)

    # ═══════════════════════════════════════════════════
    #  PostGIS: Find Nearby Cargo
    # ═══════════════════════════════════════════════════

    async def find_nearby_cargo(
        self,
        req: OptimizeRouteRequest,
    ) -> list[NearbyCargoItem]:
        """
        Query the MarketNeed table using PostGIS ST_DWithin to find
        unfulfilled cargo within `radius_km` of the route line.

        For each result, compute detour distance and profit_per_km.
        """
        # Create a PostGIS point for the route midpoint (center of search)
        mid_lat = (req.current_lat + req.dest_lat) / 2
        mid_lng = (req.current_lng + req.dest_lng) / 2
        center_point = WKTElement(
            f"POINT({mid_lng} {mid_lat})", srid=4326
        )

        # Convert radius to degrees (rough: 1° ≈ 111 km)
        radius_deg = req.radius_km / 111.0

        # Query unfulfilled MarketNeeds with a pickup_location within radius
        stmt = (
            select(
                MarketNeed,
                ST_X(MarketNeed.pickup_location).label("lng"),
                ST_Y(MarketNeed.pickup_location).label("lat"),
                cast(
                    ST_Distance(
                        MarketNeed.pickup_location,
                        center_point,
                        use_spheroid=True,
                    ),
                    Float,
                ).label("distance_m"),
            )
            .where(
                MarketNeed.is_fulfilled == False,  # noqa: E712
                MarketNeed.pickup_location.isnot(None),
                MarketNeed.quantity_kg <= req.remaining_capacity_kg,
                ST_DWithin(
                    MarketNeed.pickup_location,
                    center_point,
                    radius_deg,
                ),
            )
            .order_by("distance_m")
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        cargo_items: list[NearbyCargoItem] = []
        for row in rows:
            need = row[0]
            lng = float(row.lng)
            lat = float(row.lat)

            weight = float(need.quantity_kg)
            price = float(need.max_price_per_kg or 0)
            payout = weight * price

            detour_km = self.calculate_detour(
                lat, lng,
                req.current_lat, req.current_lng,
                req.dest_lat, req.dest_lng,
            )

            profit_per_km = payout / detour_km if detour_km > 0 else 0

            cargo_items.append(NearbyCargoItem(
                id=str(need.id),
                product_name=need.product_name,
                weight_kg=weight,
                max_price_per_kg=price,
                payout=round(payout, 2),
                destination=need.destination,
                lat=round(lat, 6),
                lng=round(lng, 6),
                detour_km=round(detour_km, 2),
                profit_per_km=round(profit_per_km, 2),
                selected=False,
            ))

        return cargo_items

    # ═══════════════════════════════════════════════════
    #  Greedy Pooling Algorithm
    # ═══════════════════════════════════════════════════

    @staticmethod
    def greedy_select(
        cargo_items: list[NearbyCargoItem],
        remaining_capacity: float,
    ) -> tuple[list[NearbyCargoItem], list[GreedyStepExplanation]]:
        """
        Greedy knapsack: sort cargo by profit_per_km (desc),
        then greedily pick items that fit the remaining capacity.

        Returns:
            - selected: list of chosen cargo items (with selected=True)
            - steps: algorithm explanation trace
        """
        # Sort by profit per km descending (most efficient detour first)
        sorted_cargo = sorted(
            cargo_items, key=lambda c: c.profit_per_km, reverse=True
        )

        selected: list[NearbyCargoItem] = []
        steps: list[GreedyStepExplanation] = []
        capacity_left = remaining_capacity

        for i, item in enumerate(sorted_cargo, 1):
            fits = item.weight_kg <= capacity_left

            if fits:
                item.selected = True
                selected.append(item)
                capacity_left -= item.weight_kg
                reason = (
                    f"✅ Selected: {item.weight_kg} kg fits "
                    f"(remaining: {capacity_left:.0f} kg). "
                    f"Payout ${item.payout:.0f} for {item.detour_km:.1f} km detour."
                )
            else:
                reason = (
                    f"❌ Skipped: {item.weight_kg} kg exceeds "
                    f"remaining capacity ({capacity_left:.0f} kg)."
                )

            steps.append(GreedyStepExplanation(
                step=i,
                product_name=item.product_name,
                weight_kg=item.weight_kg,
                profit_per_km=item.profit_per_km,
                fits=fits,
                reason=reason,
            ))

        return selected, steps

    # ═══════════════════════════════════════════════════
    #  Build Optimized Route
    # ═══════════════════════════════════════════════════

    def build_response(
        self,
        req: OptimizeRouteRequest,
        all_cargo: list[NearbyCargoItem],
        selected: list[NearbyCargoItem],
        steps: list[GreedyStepExplanation],
    ) -> OptimizeRouteResponse:
        """
        Compose the final response with Leaflet-ready waypoints,
        utilization metrics, and CO₂ savings.
        """
        # ── Waypoints ──
        waypoints: list[OptimizedWaypoint] = []

        # Current position
        waypoints.append(OptimizedWaypoint(
            lat=req.current_lat,
            lng=req.current_lng,
            label="Driver Position",
            type="current",
            icon="truck",
        ))

        # Pickup waypoints (sorted by distance from current position)
        sorted_pickups = sorted(
            selected,
            key=lambda c: self.haversine(
                req.current_lat, req.current_lng, c.lat, c.lng
            ),
        )
        for cargo in sorted_pickups:
            waypoints.append(OptimizedWaypoint(
                lat=cargo.lat,
                lng=cargo.lng,
                label=f"Pickup: {cargo.product_name} ({cargo.weight_kg:.0f} kg)",
                type="pickup",
                icon="box",
                cargo_kg=cargo.weight_kg,
                payout=cargo.payout,
                product_name=cargo.product_name,
            ))

        # Destination
        waypoints.append(OptimizedWaypoint(
            lat=req.dest_lat,
            lng=req.dest_lng,
            label="Destination",
            type="destination",
            icon="flag",
        ))

        # ── Metrics ──
        total_profit = sum(c.payout for c in selected)
        total_added_km = sum(c.detour_km for c in selected)
        total_added_min = (total_added_km / AVG_SPEED_KMH) * 60
        added_weight = sum(c.weight_kg for c in selected)
        new_load = req.current_load_kg + added_weight
        new_utilization = (new_load / req.truck_capacity_kg) * 100

        # CO₂ savings: pooling avoids separate round trips
        co2_saved = sum(
            c.detour_km * CO2_PER_KM_SAVED
            for c in selected
        )

        return OptimizeRouteResponse(
            waypoints=waypoints,
            nearby_cargo=all_cargo,
            selected_cargo=selected,
            total_profit_boost=round(total_profit, 2),
            added_distance_km=round(total_added_km, 2),
            added_time_min=round(total_added_min, 1),
            new_load_kg=round(new_load, 2),
            new_utilization_pct=round(min(new_utilization, 100), 1),
            co2_saved_kg=round(co2_saved, 2),
            algorithm_steps=steps,
        )

    # ═══════════════════════════════════════════════════
    #  Main Entry Point
    # ═══════════════════════════════════════════════════

    async def optimize(self, req: OptimizeRouteRequest) -> OptimizeRouteResponse:
        """
        Full optimization pipeline:
        1. Find nearby cargo via PostGIS
        2. Run greedy selection
        3. Build Leaflet-ready response
        """
        # 1. Spatial query
        all_cargo = await self.find_nearby_cargo(req)
        logger.info("Found %d nearby cargo items within %d km", len(all_cargo), req.radius_km)

        # 2. Greedy selection
        selected, steps = self.greedy_select(all_cargo, req.remaining_capacity_kg)
        logger.info("Greedy algorithm selected %d items", len(selected))

        # 3. Build response
        return self.build_response(req, all_cargo, selected, steps)
