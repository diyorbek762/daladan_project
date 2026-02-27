"""
Daladan Platform — Escrow Payment Router
Trustless payment holding system with:
  - Cryptographic PIN verification (bcrypt)
  - Pessimistic row locking (SELECT … FOR UPDATE)
  - Atomic SQLAlchemy transactions
  - Strict idempotency checks
  - 90/10 producer/driver split
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.auth import RoleChecker, get_current_user

from backend.database import async_session
from backend.models import (
    DealGroup,
    EscrowStatus,
    EscrowTransaction,
    Shipment,
    ShipmentStatus,
    User,
)
from backend.schemas.escrow import (
    BalanceCredit,
    EscrowReleaseRequest,
    EscrowReleaseResponse,
    EscrowStatusResponse,
)

logger = logging.getLogger("daladan.escrow")

router = APIRouter(prefix="/api/escrow", tags=["Escrow"])

# ── Split percentages ──
PRODUCER_SHARE = Decimal("0.90")
DRIVER_SHARE = Decimal("0.10")


def _verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a plaintext PIN against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_pin.encode("utf-8"),
        hashed_pin.encode("utf-8"),
    )


def _hash_pin(plain_pin: str) -> str:
    """Hash a plaintext PIN with bcrypt."""
    return bcrypt.hashpw(
        plain_pin.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# ═══════════════════════════════════════════════════════
#  POST /api/escrow/release
# ═══════════════════════════════════════════════════════

@router.post(
    "/release",
    response_model=EscrowReleaseResponse,
    dependencies=[Depends(RoleChecker(["retailer"]))],
)
async def release_escrow(request: EscrowReleaseRequest):
    """
    Release held escrow funds with strict security guarantees.

    Flow:
    1. Idempotency check — if key was already used, return cached result
    2. Begin atomic transaction
    3. Pessimistic lock on the EscrowTransaction row (FOR UPDATE)
    4. Verify escrow is in HELD state
    5. Verify cryptographic PIN against payer's stored hash
    6. Update escrow status → FUNDS_RELEASED
    7. Credit producer balance (90%)
    8. Credit driver balance (10%)
    9. Update shipment → DELIVERED
    10. Commit atomically
    """

    async with async_session() as session:
        # ─────────────────────────────────────────────
        # Step 1: Idempotency check (before transaction)
        # ─────────────────────────────────────────────
        if request.idempotency_key:
            existing = await session.execute(
                select(EscrowTransaction).where(
                    EscrowTransaction.idempotency_key == request.idempotency_key
                )
            )
            existing_escrow = existing.scalar_one_or_none()
            if existing_escrow is not None:
                if existing_escrow.status == EscrowStatus.FUNDS_RELEASED:
                    logger.info(
                        "Idempotent replay for key=%s, escrow already released",
                        request.idempotency_key,
                    )
                    # Fetch deal info for the cached response
                    deal_result = await session.execute(
                        select(DealGroup).where(
                            DealGroup.id == existing_escrow.deal_group_id
                        )
                    )
                    deal = deal_result.scalar_one()
                    return EscrowReleaseResponse(
                        status="funds_released",
                        deal_number=deal.deal_number,
                        deal_title=deal.title,
                        escrow_id=str(existing_escrow.id),
                        amount=float(existing_escrow.amount),
                        currency=existing_escrow.currency,
                        producer_credit=BalanceCredit(
                            user_id="cached", user_name="cached",
                            role="producer",
                            amount=float(existing_escrow.amount * PRODUCER_SHARE),
                            percentage=90,
                        ),
                        driver_credit=BalanceCredit(
                            user_id="cached", user_name="cached",
                            role="driver",
                            amount=float(existing_escrow.amount * DRIVER_SHARE),
                            percentage=10,
                        ),
                        released_at=existing_escrow.released_at or datetime.utcnow(),
                        idempotency_key=request.idempotency_key,
                        message="Idempotent replay — funds were already released.",
                    )
                else:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Idempotency key exists but escrow is in "
                               f"'{existing_escrow.status.value}' state, not released.",
                    )

        # ─────────────────────────────────────────────
        # Step 2-10: Atomic transaction with pessimistic locking
        # ─────────────────────────────────────────────
        async with session.begin():

            # ── Step 2-3: Fetch deal group ──
            deal_result = await session.execute(
                select(DealGroup).where(DealGroup.id == request.deal_id)
            )
            deal = deal_result.scalar_one_or_none()
            if not deal:
                raise HTTPException(
                    status_code=404,
                    detail=f"Deal {request.deal_id} not found.",
                )

            # ── Step 3: Lock escrow row with FOR UPDATE ──
            escrow_result = await session.execute(
                select(EscrowTransaction)
                .where(EscrowTransaction.deal_group_id == deal.id)
                .with_for_update()  # Pessimistic lock — blocks concurrent access
            )
            escrow = escrow_result.scalar_one_or_none()
            if not escrow:
                raise HTTPException(
                    status_code=404,
                    detail=f"No escrow transaction found for deal #{deal.deal_number}.",
                )

            # ── Step 4: Verify HELD state (strict idempotency) ──
            if escrow.status == EscrowStatus.FUNDS_RELEASED:
                raise HTTPException(
                    status_code=409,
                    detail="Funds have already been released for this deal. "
                           "Double-spending prevented.",
                )
            if escrow.status != EscrowStatus.HELD:
                raise HTTPException(
                    status_code=400,
                    detail=f"Escrow is in '{escrow.status.value}' state. "
                           f"Only 'held' escrows can be released.",
                )

            # ── Step 5: Verify cryptographic PIN ──
            payer_result = await session.execute(
                select(User)
                .where(User.id == escrow.payer_id)
                .with_for_update()  # Lock payer row too
            )
            payer = payer_result.scalar_one_or_none()
            if not payer:
                raise HTTPException(
                    status_code=404,
                    detail="Payer account not found.",
                )

            if not payer.escrow_pin_hash:
                raise HTTPException(
                    status_code=403,
                    detail="Payer has no escrow PIN configured. "
                           "Cannot authorize release.",
                )

            if not _verify_pin(request.pin, payer.escrow_pin_hash):
                logger.warning(
                    "Invalid PIN attempt for deal #%d by payer %s",
                    deal.deal_number, payer.id,
                )
                raise HTTPException(
                    status_code=403,
                    detail="Invalid PIN. Authorization denied.",
                )

            # ── Step 6: Update escrow → FUNDS_RELEASED ──
            now = datetime.utcnow()
            escrow.status = EscrowStatus.FUNDS_RELEASED
            escrow.released_at = now
            escrow.released_by_id = payer.id
            if request.idempotency_key:
                escrow.idempotency_key = request.idempotency_key

            # ── Step 7: Credit Producer's balance (90%) ──
            producer_result = await session.execute(
                select(User)
                .where(User.id == deal.seller_id)
                .with_for_update()  # Lock producer row
            )
            producer = producer_result.scalar_one_or_none()
            if not producer:
                raise HTTPException(
                    status_code=404,
                    detail="Producer (seller) account not found.",
                )

            producer_amount = escrow.amount * PRODUCER_SHARE
            producer.balance = (producer.balance or Decimal("0")) + producer_amount

            # ── Step 8: Credit Driver's balance (10%) ──
            driver_result = await session.execute(
                select(User)
                .where(User.id == deal.driver_id)
                .with_for_update()  # Lock driver row
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                raise HTTPException(
                    status_code=404,
                    detail="Driver account not found.",
                )

            driver_amount = escrow.amount * DRIVER_SHARE
            driver.balance = (driver.balance or Decimal("0")) + driver_amount

            # ── Step 9: Update shipment → DELIVERED ──
            shipment_result = await session.execute(
                select(Shipment)
                .where(Shipment.deal_group_id == deal.id)
                .with_for_update()
            )
            shipment = shipment_result.scalar_one_or_none()
            if shipment:
                shipment.status = ShipmentStatus.DELIVERED
                shipment.delivered_at = now

            # ── Step 10: Transaction auto-commits on exit ──
            logger.info(
                "✅ Escrow released: Deal #%d, $%.2f → "
                "Producer %s (+$%.2f), Driver %s (+$%.2f)",
                deal.deal_number, escrow.amount,
                producer.full_name, producer_amount,
                driver.full_name, driver_amount,
            )

            return EscrowReleaseResponse(
                status="funds_released",
                deal_number=deal.deal_number,
                deal_title=deal.title,
                escrow_id=str(escrow.id),
                amount=float(escrow.amount),
                currency=escrow.currency,
                producer_credit=BalanceCredit(
                    user_id=str(producer.id),
                    user_name=producer.full_name,
                    role="producer",
                    amount=float(producer_amount),
                    percentage=90,
                ),
                driver_credit=BalanceCredit(
                    user_id=str(driver.id),
                    user_name=driver.full_name,
                    role="driver",
                    amount=float(driver_amount),
                    percentage=10,
                ),
                released_at=now,
                idempotency_key=request.idempotency_key,
                message=(
                    f"Funds released for Deal #{deal.deal_number} — "
                    f"{deal.title}. ${float(producer_amount):.2f} credited "
                    f"to {producer.full_name}, ${float(driver_amount):.2f} "
                    f"credited to {driver.full_name}."
                ),
            )


# ═══════════════════════════════════════════════════════
#  GET /api/escrow/{deal_id}
# ═══════════════════════════════════════════════════════

@router.get(
    "/{deal_id}",
    response_model=EscrowStatusResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_escrow_status(deal_id: uuid.UUID):
    """Check the current status of an escrow transaction."""

    async with async_session() as session:
        deal_result = await session.execute(
            select(DealGroup).where(DealGroup.id == deal_id)
        )
        deal = deal_result.scalar_one_or_none()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found.")

        escrow_result = await session.execute(
            select(EscrowTransaction).where(
                EscrowTransaction.deal_group_id == deal.id
            )
        )
        escrow = escrow_result.scalar_one_or_none()
        if not escrow:
            raise HTTPException(
                status_code=404,
                detail="No escrow transaction for this deal.",
            )

        # Fetch payer/payee names
        payer_name = None
        payee_name = None
        if escrow.payer_id:
            payer_r = await session.execute(
                select(User.full_name).where(User.id == escrow.payer_id)
            )
            payer_name = payer_r.scalar_one_or_none()
        if escrow.payee_id:
            payee_r = await session.execute(
                select(User.full_name).where(User.id == escrow.payee_id)
            )
            payee_name = payee_r.scalar_one_or_none()

        return EscrowStatusResponse(
            escrow_id=str(escrow.id),
            deal_number=deal.deal_number,
            amount=float(escrow.amount),
            currency=escrow.currency,
            status=escrow.status.value,
            payer=payer_name,
            payee=payee_name,
            created_at=escrow.created_at,
            released_at=escrow.released_at,
        )
