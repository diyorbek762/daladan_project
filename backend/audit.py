"""
Daladan Platform — Audit Event Listeners
Automatically logs all state changes to EscrowTransaction and DealGroup
into an immutable AuditLog table using SQLAlchemy event listeners.
"""
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import event, inspect

from backend.database import async_session

logger = logging.getLogger("daladan.audit")


def _serialize_value(value):
    """Convert a value to a JSON-serializable format."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):  # Enum
        return value.value
    return str(value)


def _get_changes(instance) -> dict:
    """
    Inspect a SQLAlchemy instance and return a dict of changed attributes.
    Each key maps to {"old": ..., "new": ...}.
    """
    insp = inspect(instance)
    changes = {}

    for attr in insp.attrs:
        hist = attr.history
        if hist.has_changes():
            old_val = hist.deleted[0] if hist.deleted else None
            new_val = hist.added[0] if hist.added else None
            changes[attr.key] = {
                "old": _serialize_value(old_val),
                "new": _serialize_value(new_val),
            }

    return changes


def _get_snapshot(instance) -> dict:
    """Get a full snapshot of the instance's current column values."""
    insp = inspect(instance)
    snapshot = {}
    for attr in insp.mapper.column_attrs:
        value = getattr(instance, attr.key, None)
        snapshot[attr.key] = _serialize_value(value)
    return snapshot


async def _write_audit_log(
    action: str,
    table_name: str,
    record_id: str,
    changes: dict,
    snapshot: dict,
):
    """Write an audit log entry asynchronously."""
    from backend.models import AuditLog

    try:
        async with async_session() as session:
            async with session.begin():
                log_entry = AuditLog(
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    changes=json.dumps(changes, default=str),
                    snapshot=json.dumps(snapshot, default=str),
                )
                session.add(log_entry)

        logger.info(
            "📝 Audit: %s on %s [%s] — %d field(s) changed",
            action, table_name, record_id, len(changes),
        )
    except Exception as exc:
        # Audit logging must never crash the main transaction
        logger.error("Failed to write audit log: %s", exc)


def register_audit_listeners():
    """
    Register SQLAlchemy ORM event listeners for EscrowTransaction and DealGroup.
    These fire after_insert and after_update to capture all state changes.
    """
    from backend.models import EscrowTransaction, DealGroup

    # ── EscrowTransaction listeners ──

    @event.listens_for(EscrowTransaction, "after_insert")
    def escrow_after_insert(mapper, connection, target):
        import asyncio
        snapshot = _get_snapshot(target)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write_audit_log(
                action="INSERT",
                table_name="escrow_transactions",
                record_id=str(target.id),
                changes={},
                snapshot=snapshot,
            ))
        except RuntimeError:
            logger.info("📝 Audit (sync): INSERT escrow_transactions [%s]", target.id)

    @event.listens_for(EscrowTransaction, "after_update")
    def escrow_after_update(mapper, connection, target):
        import asyncio
        changes = _get_changes(target)
        if not changes:
            return
        snapshot = _get_snapshot(target)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write_audit_log(
                action="UPDATE",
                table_name="escrow_transactions",
                record_id=str(target.id),
                changes=changes,
                snapshot=snapshot,
            ))
        except RuntimeError:
            logger.info(
                "📝 Audit (sync): UPDATE escrow_transactions [%s] — %s",
                target.id, list(changes.keys()),
            )

    # ── DealGroup listeners ──

    @event.listens_for(DealGroup, "after_insert")
    def deal_after_insert(mapper, connection, target):
        import asyncio
        snapshot = _get_snapshot(target)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write_audit_log(
                action="INSERT",
                table_name="deal_groups",
                record_id=str(target.id),
                changes={},
                snapshot=snapshot,
            ))
        except RuntimeError:
            logger.info("📝 Audit (sync): INSERT deal_groups [%s]", target.id)

    @event.listens_for(DealGroup, "after_update")
    def deal_after_update(mapper, connection, target):
        import asyncio
        changes = _get_changes(target)
        if not changes:
            return
        snapshot = _get_snapshot(target)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write_audit_log(
                action="UPDATE",
                table_name="deal_groups",
                record_id=str(target.id),
                changes=changes,
                snapshot=snapshot,
            ))
        except RuntimeError:
            logger.info(
                "📝 Audit (sync): UPDATE deal_groups [%s] — %s",
                target.id, list(changes.keys()),
            )

    logger.info("✅ Audit event listeners registered for EscrowTransaction and DealGroup")
