"""
Daladan Platform — Seed Script
Creates initial dummy data for Namangan and Tashkent regions.
Called on first startup if tables are empty.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    User, UserRole,
    Inventory,
    MarketNeed,
    DealGroup, DealStatus,
    Message,
    Shipment, ShipmentStatus,
    EscrowTransaction, EscrowStatus,
)
from geoalchemy2 import WKTElement
import bcrypt
from passlib.context import CryptContext

# Demo PIN: "1234" (pre-hashed for seed)
_DEMO_PIN_HASH = bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode("utf-8")

# Demo password: "password123" (pre-hashed for seed)
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_DEMO_PASSWORD_HASH = _pwd_ctx.hash("password123")

from backend.encryption import encrypt_pii


async def seed_database(session: AsyncSession) -> None:
    """Insert seed data if the users table is empty."""

    result = await session.execute(select(User).limit(1))
    if result.scalar_one_or_none() is not None:
        print("⏭  Database already seeded — skipping.")
        return

    print("🌱 Seeding database with dummy data…")

    # ── Users ──
    producer = User(
        id=uuid.UUID("a1b2c3d4-0001-4000-8000-000000000001"),
        full_name="Namangan Valley Farms",
        email="farm@namangan.uz",
        phone_encrypted=encrypt_pii("+998901234567"),
        role=UserRole.PRODUCER,
        region="Namangan",
        is_verified=True,
        password_hash=_DEMO_PASSWORD_HASH,
    )
    retailer = User(
        id=uuid.UUID("a1b2c3d4-0002-4000-8000-000000000002"),
        full_name="Korzinka Market",
        email="buyer@korzinka.uz",
        phone_encrypted=encrypt_pii("+998901234568"),
        role=UserRole.RETAILER,
        region="Tashkent",
        is_verified=True,
        password_hash=_DEMO_PASSWORD_HASH,
        escrow_pin_hash=_DEMO_PIN_HASH,  # Demo PIN: "1234"
    )
    driver = User(
        id=uuid.UUID("a1b2c3d4-0003-4000-8000-000000000003"),
        full_name="Alisher Karimov",
        email="alisher.driver@daladan.uz",
        phone_encrypted=encrypt_pii("+998901234569"),
        role=UserRole.DRIVER,
        region="Tashkent",
        is_verified=True,
        password_hash=_DEMO_PASSWORD_HASH,
    )
    producer2 = User(
        id=uuid.UUID("a1b2c3d4-0004-4000-8000-000000000004"),
        full_name="Fergana Organic Farm",
        email="organic@fergana.uz",
        phone_encrypted=encrypt_pii("+998901234570"),
        role=UserRole.PRODUCER,
        region="Fergana",
        is_verified=True,
        password_hash=_DEMO_PASSWORD_HASH,
    )
    retailer2 = User(
        id=uuid.UUID("a1b2c3d4-0005-4000-8000-000000000005"),
        full_name="Samarkand Agro Co.",
        email="agro@samarkand.uz",
        phone_encrypted=encrypt_pii("+998901234571"),
        role=UserRole.PRODUCER,
        region="Samarkand",
        is_verified=True,
        password_hash=_DEMO_PASSWORD_HASH,
    )

    session.add_all([producer, retailer, driver, producer2, retailer2])
    await session.flush()

    # ── Inventory ──
    inv_apples = Inventory(
        owner_id=producer.id,
        product_name="Golden Apples",
        variety="Grade A Organic",
        quantity_kg=Decimal("1200"),
        price_per_kg=Decimal("3.80"),
        description="Premium golden apples harvested from Namangan orchards.",
        region="Namangan",
        is_organic=True,
        image_url="https://images.unsplash.com/photo-1619546813926-a78fa6372cd2?w=500&h=350&fit=crop",
    )
    inv_tomatoes = Inventory(
        owner_id=producer.id,
        product_name="Cherry Tomatoes",
        variety="Vine-ripened",
        quantity_kg=Decimal("800"),
        price_per_kg=Decimal("3.10"),
        description="Sweet vine-ripened cherry tomatoes from greenhouse.",
        region="Tashkent",
        is_organic=True,
        image_url="https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500&h=350&fit=crop",
    )
    inv_carrots = Inventory(
        owner_id=producer2.id,
        product_name="Fresh Carrots",
        variety="Sweet variety",
        quantity_kg=Decimal("1500"),
        price_per_kg=Decimal("2.40"),
        description="Naturally sweet carrots from Fergana valley.",
        region="Fergana",
        is_organic=False,
        image_url="https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=500&h=350&fit=crop",
    )
    inv_onions = Inventory(
        owner_id=retailer2.id,
        product_name="Red Onions",
        variety="Grade A",
        quantity_kg=Decimal("2000"),
        price_per_kg=Decimal("1.60"),
        description="Premium red onions from Samarkand fields.",
        region="Samarkand",
        is_organic=False,
        image_url="https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=500&h=350&fit=crop",
    )

    session.add_all([inv_apples, inv_tomatoes, inv_carrots, inv_onions])
    await session.flush()

    # ── Market Needs (with PostGIS pickup locations) ──
    need1 = MarketNeed(
        requester_id=retailer.id,
        product_name="Carrots",
        quantity_kg=Decimal("2000"),
        max_price_per_kg=Decimal("2.50"),
        delivery_by=datetime.utcnow() + timedelta(days=7),
        destination="Korzinka Sergeli, Tashkent",
        pickup_location=WKTElement("POINT(69.2163 41.2647)", srid=4326),
        notes="Need fresh carrots for weekly retail stock.",
    )
    need2 = MarketNeed(
        requester_id=retailer.id,
        product_name="Pomegranates",
        quantity_kg=Decimal("500"),
        max_price_per_kg=Decimal("5.50"),
        delivery_by=datetime.utcnow() + timedelta(days=14),
        destination="Korzinka Chorsu, Tashkent",
        pickup_location=WKTElement("POINT(69.2794 41.3111)", srid=4326),
        notes="Premium organic pomegranates for seasonal display.",
    )
    # Nearby cargo along the Namangan → Tashkent corridor
    need3 = MarketNeed(
        requester_id=retailer.id,
        product_name="Onions",
        quantity_kg=Decimal("480"),
        max_price_per_kg=Decimal("1.80"),
        delivery_by=datetime.utcnow() + timedelta(days=3),
        destination="Chorsu Market, Tashkent",
        pickup_location=WKTElement("POINT(69.6200 41.0300)", srid=4326),  # Near Angren
        notes="Red onions for wholesale distribution.",
    )
    need4 = MarketNeed(
        requester_id=producer2.id,
        product_name="Melons",
        quantity_kg=Decimal("600"),
        max_price_per_kg=Decimal("2.20"),
        delivery_by=datetime.utcnow() + timedelta(days=5),
        destination="Yunusabad Market, Tashkent",
        pickup_location=WKTElement("POINT(70.6500 40.8200)", srid=4326),  # Near Pap
        notes="Seasonal melons for retail.",
    )
    need5 = MarketNeed(
        requester_id=retailer2.id,
        product_name="Dried Fruits",
        quantity_kg=Decimal("200"),
        max_price_per_kg=Decimal("8.00"),
        delivery_by=datetime.utcnow() + timedelta(days=10),
        destination="Export Terminal, Tashkent",
        pickup_location=WKTElement("POINT(71.1400 40.9050)", srid=4326),  # Near Chust
        notes="Premium dried apricots for export.",
    )
    need6 = MarketNeed(
        requester_id=retailer.id,
        product_name="Potatoes",
        quantity_kg=Decimal("350"),
        max_price_per_kg=Decimal("1.50"),
        delivery_by=datetime.utcnow() + timedelta(days=4),
        destination="Sergeli Depot, Tashkent",
        pickup_location=WKTElement("POINT(69.4200 41.0800)", srid=4326),  # Near Olmaliq
        notes="Fresh potatoes for restaurant chain.",
    )
    need7 = MarketNeed(
        requester_id=retailer.id,
        product_name="Cabbage",
        quantity_kg=Decimal("700"),
        max_price_per_kg=Decimal("1.20"),
        delivery_by=datetime.utcnow() + timedelta(days=6),
        destination="Mega Planet, Tashkent",
        pickup_location=WKTElement("POINT(69.2500 41.1500)", srid=4326),  # Near Sergeli
        notes="White cabbage for supermarket chain.",
    )

    session.add_all([need1, need2, need3, need4, need5, need6, need7])
    await session.flush()

    # ── Deal Group #901 ──
    deal = DealGroup(
        deal_number=901,
        title="Golden Apples",
        status=DealStatus.AGREED,
        seller_id=producer.id,
        buyer_id=retailer.id,
        driver_id=driver.id,
        agreed_price_per_kg=Decimal("3.65"),
        agreed_quantity_kg=Decimal("1200"),
    )
    session.add(deal)
    await session.flush()

    # ── Messages for Deal #901 ──
    msgs = [
        Message(
            deal_group_id=deal.id, sender_id=producer.id,
            content="Assalomu alaykum! We have 1,200 kg of Golden Apples ready — Grade A, harvested yesterday. Price: $3.80/kg. Can deliver by Friday.",
            created_at=datetime(2026, 2, 25, 10, 14),
        ),
        Message(
            deal_group_id=deal.id, sender_id=retailer.id,
            content="Wa alaykum assalom! We need 1,000 kg minimum. Can you do $3.50/kg for a recurring weekly order?",
            created_at=datetime(2026, 2, 25, 10, 32),
        ),
        Message(
            deal_group_id=deal.id, sender_id=producer.id,
            content="$3.50 is tight for Grade A organic. How about $3.65/kg for the weekly commitment?",
            created_at=datetime(2026, 2, 25, 10, 48),
        ),
        Message(
            deal_group_id=deal.id, sender_id=retailer.id,
            content="Deal — $3.65/kg for 1,200 kg weekly. ✅ Please confirm delivery schedule. Gate B-4 before 6 AM.",
            created_at=datetime(2026, 2, 25, 11, 5),
        ),
        Message(
            deal_group_id=deal.id, sender_id=None, is_system=True,
            content="✅ Price agreed: $3.65/kg × 1,200 kg = $4,380/week",
            created_at=datetime(2026, 2, 25, 11, 6),
        ),
        Message(
            deal_group_id=deal.id, sender_id=driver.id,
            content="Salom! I can handle the weekly run. Namangan → Tashkent, depart at 2 AM, arrive 5:30 AM at Gate B-4. Refrigerated truck, 2,400 kg capacity.",
            created_at=datetime(2026, 2, 25, 11, 22),
        ),
    ]
    session.add_all(msgs)
    await session.flush()

    # ── Shipment ──
    shipment = Shipment(
        deal_group_id=deal.id,
        driver_id=driver.id,
        origin_name="Namangan Warehouse",
        destination_name="Korzinka Gate B-4, Tashkent",
        status=ShipmentStatus.IN_TRANSIT,
        total_weight_kg=Decimal("1920"),
        truck_capacity_kg=Decimal("2400"),
        eta_minutes=18,
        departed_at=datetime(2026, 2, 27, 2, 0),
    )
    session.add(shipment)
    await session.flush()

    # ── Escrow ──
    escrow = EscrowTransaction(
        deal_group_id=deal.id,
        amount=Decimal("4380.00"),
        currency="USD",
        status=EscrowStatus.HELD,
        payer_id=retailer.id,
        payee_id=producer.id,
    )
    session.add(escrow)

    await session.commit()
    print("✅ Seed data inserted successfully!")
