"""
Daladan Platform — SQLAlchemy ORM Models
All tables use UUID primary keys. Shipment includes a PostGIS Geometry column.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from backend.database import Base


# ═══════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════

import enum


class UserRole(str, enum.Enum):
    PRODUCER = "producer"
    DRIVER = "driver"
    RETAILER = "retailer"
    ADMIN = "admin"


class DealStatus(str, enum.Enum):
    NEGOTIATING = "negotiating"
    AGREED = "agreed"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    LOADING = "loading"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class EscrowStatus(str, enum.Enum):
    HELD = "held"
    RELEASED = "released"
    FUNDS_RELEASED = "funds_released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


# ═══════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════


class User(Base):
    """Platform user — can be Producer, Driver, or Retailer."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=True)  # passlib bcrypt hash
    phone_encrypted = Column(String(512), nullable=True)  # Fernet-encrypted phone number
    role = Column(SAEnum(UserRole, name="user_role_enum"), nullable=False)
    region = Column(String(100), nullable=True)  # e.g. "Namangan", "Tashkent"
    is_verified = Column(Boolean, default=False)
    balance = Column(Numeric(12, 2), default=0, nullable=False)  # account balance in USD
    escrow_pin_hash = Column(String(128), nullable=True)  # bcrypt-hashed escrow release PIN
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_items = relationship("Inventory", back_populates="owner")
    market_needs = relationship("MarketNeed", back_populates="requester")
    sent_messages = relationship("Message", back_populates="sender")
    shipments_as_driver = relationship(
        "Shipment", back_populates="driver", foreign_keys="Shipment.driver_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.full_name} ({self.role.value})>"


class Inventory(Base):
    """Producer's produce inventory — a batch of a specific product."""
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_name = Column(String(150), nullable=False)  # e.g. "Golden Apples"
    variety = Column(String(100), nullable=True)  # e.g. "Grade A Organic"
    quantity_kg = Column(Numeric(10, 2), nullable=False)
    price_per_kg = Column(Numeric(8, 2), nullable=False)
    description = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)  # AI-generated description
    region = Column(String(100), nullable=True)
    is_organic = Column(Boolean, default=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="inventory_items")

    def __repr__(self) -> str:
        return f"<Inventory {self.product_name} — {self.quantity_kg}kg>"


class MarketNeed(Base):
    """Retailer's bulk produce request — visible to producers."""
    __tablename__ = "market_needs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_name = Column(String(150), nullable=False)
    quantity_kg = Column(Numeric(10, 2), nullable=False)
    max_price_per_kg = Column(Numeric(8, 2), nullable=True)
    delivery_by = Column(DateTime, nullable=True)
    destination = Column(String(200), nullable=True)
    pickup_location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )  # PostGIS point for spatial queries
    notes = Column(Text, nullable=True)
    is_fulfilled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    requester = relationship("User", back_populates="market_needs")

    def __repr__(self) -> str:
        return f"<MarketNeed {self.product_name} — {self.quantity_kg}kg>"


class DealGroup(Base):
    """Multi-party deal negotiation group (Seller + Buyer + Driver)."""
    __tablename__ = "deal_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_number = Column(Integer, unique=True, nullable=False)  # e.g. 901
    title = Column(String(200), nullable=False)  # e.g. "Golden Apples"
    status = Column(
        SAEnum(DealStatus, name="deal_status_enum"),
        default=DealStatus.NEGOTIATING,
    )
    seller_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    buyer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    driver_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    agreed_price_per_kg = Column(Numeric(8, 2), nullable=True)
    agreed_quantity_kg = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("Message", back_populates="deal_group", order_by="Message.created_at")

    def __repr__(self) -> str:
        return f"<DealGroup #{self.deal_number} — {self.title}>"


class Message(Base):
    """Chat message within a DealGroup."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_group_id = Column(
        UUID(as_uuid=True), ForeignKey("deal_groups.id", ondelete="CASCADE"), nullable=False
    )
    sender_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content = Column(Text, nullable=False)
    is_system = Column(Boolean, default=False)  # system-generated message
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deal_group = relationship("DealGroup", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")

    def __repr__(self) -> str:
        return f"<Message in Deal#{self.deal_group_id} by {self.sender_id}>"


class Shipment(Base):
    """A freight shipment between origin and destination with PostGIS tracking."""
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_group_id = Column(
        UUID(as_uuid=True), ForeignKey("deal_groups.id"), nullable=True
    )
    driver_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    origin_name = Column(String(200), nullable=False)
    destination_name = Column(String(200), nullable=False)
    status = Column(
        SAEnum(ShipmentStatus, name="shipment_status_enum"),
        default=ShipmentStatus.PENDING,
    )
    total_weight_kg = Column(Numeric(10, 2), nullable=True)
    truck_capacity_kg = Column(Numeric(10, 2), default=2400)
    current_location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    eta_minutes = Column(Integer, nullable=True)
    departed_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    driver = relationship("User", back_populates="shipments_as_driver")

    def __repr__(self) -> str:
        return f"<Shipment {self.origin_name} → {self.destination_name}>"


class EscrowTransaction(Base):
    """Financial escrow for a deal — held until delivery confirmation."""
    __tablename__ = "escrow_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_group_id = Column(
        UUID(as_uuid=True), ForeignKey("deal_groups.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(
        SAEnum(EscrowStatus, name="escrow_status_enum"),
        default=EscrowStatus.HELD,
    )
    payer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    payee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    released_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    idempotency_key = Column(String(64), unique=True, nullable=True)  # prevents double-release
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Escrow ${self.amount} — {self.status.value}>"


class AuditLog(Base):
    """Immutable audit trail for financial and deal state changes."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    table_name = Column(String(100), nullable=False)  # e.g. "escrow_transactions"
    record_id = Column(String(64), nullable=False)  # UUID of the affected row
    changes = Column(Text, nullable=True)  # JSON: {"field": {"old": ..., "new": ...}}
    snapshot = Column(Text, nullable=True)  # JSON: full row snapshot at time of event
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.table_name} [{self.record_id}]>"
