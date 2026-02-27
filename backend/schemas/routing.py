"""
Daladan Platform — Routing Endpoint Pydantic Schemas
Request/response models for the Route Optimization Engine.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════
#  Request
# ═══════════════════════════════════════════════════════


class OptimizeRouteRequest(BaseModel):
    """Input for the route optimization engine."""

    model_config = {"extra": "forbid"}

    current_lat: float = Field(
        ..., ge=-90, le=90,
        description="Driver's current latitude",
        examples=[41.07],
    )
    current_lng: float = Field(
        ..., ge=-180, le=180,
        description="Driver's current longitude",
        examples=[69.40],
    )
    dest_lat: float = Field(
        ..., ge=-90, le=90,
        description="Destination latitude",
        examples=[41.31],
    )
    dest_lng: float = Field(
        ..., ge=-180, le=180,
        description="Destination longitude",
        examples=[69.28],
    )
    remaining_capacity_kg: float = Field(
        ..., gt=0, le=50_000,
        description="Remaining truck capacity in kilograms",
        examples=[480],
    )
    current_load_kg: float = Field(
        ..., ge=0, le=50_000,
        description="Current load in kilograms",
        examples=[1920],
    )
    truck_capacity_kg: float = Field(
        2400, gt=0, le=50_000,
        description="Total truck capacity in kilograms",
    )
    radius_km: float = Field(
        50, gt=0, le=200,
        description="Search radius in kilometers (default 50)",
    )


# ═══════════════════════════════════════════════════════
#  Response Components
# ═══════════════════════════════════════════════════════


class NearbyCargoItem(BaseModel):
    """An available cargo opportunity near the route."""

    id: str = Field(..., description="MarketNeed UUID")
    product_name: str
    weight_kg: float
    max_price_per_kg: float
    payout: float = Field(..., description="Total potential payout (weight × price)")
    destination: Optional[str] = None
    lat: float
    lng: float
    detour_km: float = Field(..., description="Extra km to pick up this cargo")
    profit_per_km: float = Field(..., description="Payout / detour_km ratio")
    selected: bool = Field(False, description="Whether the greedy algo selected this")


class OptimizedWaypoint(BaseModel):
    """A waypoint on the optimized route — consumable by Leaflet.js."""

    lat: float
    lng: float
    label: str = Field(..., description="Human-readable label for the marker")
    type: str = Field(
        ..., description="Waypoint type: 'current', 'pickup', or 'destination'"
    )
    icon: str = Field("circle", description="Suggested icon key for the frontend")
    cargo_kg: Optional[float] = None
    payout: Optional[float] = None
    product_name: Optional[str] = None


class GreedyStepExplanation(BaseModel):
    """One step of the greedy algorithm for transparency/debugging."""

    step: int
    product_name: str
    weight_kg: float
    profit_per_km: float
    fits: bool
    reason: str


# ═══════════════════════════════════════════════════════
#  Full Response
# ═══════════════════════════════════════════════════════


class OptimizeRouteResponse(BaseModel):
    """Structured route optimization result — Leaflet-ready."""

    # Waypoints for the map
    waypoints: list[OptimizedWaypoint] = Field(
        ..., description="Ordered waypoints: current → pickups → destination"
    )

    # Cargo details
    nearby_cargo: list[NearbyCargoItem] = Field(
        ..., description="All cargo found within radius"
    )
    selected_cargo: list[NearbyCargoItem] = Field(
        ..., description="Cargo items selected by the greedy algorithm"
    )

    # Summary metrics
    total_profit_boost: float = Field(
        ..., description="Total extra revenue from selected pickups ($)"
    )
    added_distance_km: float = Field(
        ..., description="Total extra distance from detours (km)"
    )
    added_time_min: float = Field(
        ..., description="Estimated extra time (minutes, at ~40 km/h avg)"
    )
    new_load_kg: float = Field(
        ..., description="New total load after pickups"
    )
    new_utilization_pct: float = Field(
        ..., description="New truck utilization percentage (0-100)"
    )
    co2_saved_kg: float = Field(
        ..., description="CO₂ saved by pooling vs separate trips (kg)"
    )

    # Algorithm transparency
    algorithm_steps: list[GreedyStepExplanation] = Field(
        default_factory=list,
        description="Step-by-step greedy algorithm decisions",
    )
