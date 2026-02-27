"""
Daladan Platform — Routing API Endpoint
Exposes the RouteOptimizer service via POST /api/routing/optimize.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import RoleChecker

from backend.database import async_session
from backend.schemas.routing import OptimizeRouteRequest, OptimizeRouteResponse
from backend.services.route_optimizer import RouteOptimizer

logger = logging.getLogger("daladan.routing")

router = APIRouter(prefix="/api/routing", tags=["Routing"])


@router.post(
    "/optimize",
    response_model=OptimizeRouteResponse,
    dependencies=[Depends(RoleChecker(["driver"]))],
)
async def optimize_route(request: OptimizeRouteRequest):
    """
    Location Optimization Engine endpoint.

    Accepts the driver's current position, destination, and remaining capacity.
    Returns optimized waypoints with profitable micro-detour suggestions,
    formatted for direct Leaflet.js consumption.
    """
    try:
        async with async_session() as session:
            optimizer = RouteOptimizer(session)
            result = await optimizer.optimize(request)
            return result
    except Exception as exc:
        logger.error("Route optimization failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Route optimization failed: {exc}",
        )
