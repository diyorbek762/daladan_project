"""
Daladan Platform — FastAPI Application
Serves the frontend, configures CORS, and initialises the database on startup.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import get_settings
from backend.database import engine, Base, async_session
from backend.routers.ai import router as ai_router
from backend.routers.auth import router as auth_router
from backend.routers.escrow import router as escrow_router
from backend.routers.routing import router as routing_router
from backend.seed import seed_database

# Ensure models are imported so Base.metadata knows about them
import backend.models  # noqa: F401

settings = get_settings()
logger = logging.getLogger("daladan")


# ═══════════════════════════════════════════════════════
#  LIFESPAN — startup / shutdown
# ═══════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: create tables & seed data. Cleanup on shutdown."""
    logger.info("🚀 Starting Daladan Platform…")

    # Create all tables (safe if they already exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created / verified.")

    # Register audit event listeners
    from backend.audit import register_audit_listeners
    register_audit_listeners()

    # Seed with dummy data
    async with async_session() as session:
        await seed_database(session)

    yield  # ← app runs here

    # Shutdown
    await engine.dispose()
    logger.info("👋 Daladan Platform shut down.")


# ═══════════════════════════════════════════════════════
#  APP FACTORY
# ═══════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="B2B Agricultural Supply Chain & Logistics Hub",
    lifespan=lifespan,
)


# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ── Security Headers ──
from backend.middleware.security import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# ── Rate Limiter ──
from backend.middleware.rate_limit import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Routers ──
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(escrow_router)
app.include_router(routing_router)


# ═══════════════════════════════════════════════════════
#  STATIC FILES & FRONTEND
# ═══════════════════════════════════════════════════════

# The frontend lives in the project root (one level up from backend/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main index.html at root."""
    return FileResponse(FRONTEND_DIR / "index.html")


# Serve any static assets (CSS, JS, images) from the project root
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR), html=False),
    name="static",
)


# ═══════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ═══════════════════════════════════════════════════════
#  API PLACEHOLDER ROUTES
# ═══════════════════════════════════════════════════════

@app.get("/api/inventory")
async def list_inventory():
    """List all available inventory (protected — producer & retailer)."""
    from sqlalchemy import select
    from backend.models import Inventory

    async with async_session() as session:
        result = await session.execute(
            select(Inventory).where(Inventory.is_available == True)  # noqa: E712
        )
        items = result.scalars().all()
        return [
            {
                "id": str(item.id),
                "product_name": item.product_name,
                "variety": item.variety,
                "quantity_kg": float(item.quantity_kg),
                "price_per_kg": float(item.price_per_kg),
                "region": item.region,
                "is_organic": item.is_organic,
                "image_url": item.image_url,
            }
            for item in items
        ]


@app.get("/api/deals")
async def list_deals():
    """List all deal groups (protected — all authenticated users)."""
    from sqlalchemy import select
    from backend.models import DealGroup

    async with async_session() as session:
        result = await session.execute(select(DealGroup))
        deals = result.scalars().all()
        return [
            {
                "id": str(deal.id),
                "deal_number": deal.deal_number,
                "title": deal.title,
                "status": deal.status.value,
                "agreed_price_per_kg": float(deal.agreed_price_per_kg) if deal.agreed_price_per_kg else None,
                "agreed_quantity_kg": float(deal.agreed_quantity_kg) if deal.agreed_quantity_kg else None,
            }
            for deal in deals
        ]


# ═══════════════════════════════════════════════════════
#  RUN (for direct execution)
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
