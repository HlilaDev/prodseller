"""
CRUD helpers for PendingPayment table.
"""
import random
import string
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import PendingPayment

EXPIRE_MINUTES = 30


def _gen_note() -> str:
    """Generate a unique 10-char alphanumeric note like T00LS-9BE380."""
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(random.choices(chars, k=5))
    part2 = "".join(random.choices(chars, k=6))
    return f"{part1}-{part2}"


def create_pending_payment(
    telegram_id: str,
    product_id: int,
    price: float,
    chat_id: str,
    message_id: int | None = None,
) -> PendingPayment:
    db = SessionLocal()
    # Ensure unique note
    while True:
        note = _gen_note()
        exists = db.query(PendingPayment).filter(PendingPayment.note == note).first()
        if not exists:
            break

    expires = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    pp = PendingPayment(
        telegram_id=str(telegram_id),
        product_id=product_id,
        price=price,
        note=note,
        chat_id=str(chat_id),
        message_id=message_id,
        expires_at=expires,
    )
    db.add(pp)
    db.commit()
    db.refresh(pp)
    db.close()
    return pp


def update_message_id(pending_id: int, message_id: int):
    db = SessionLocal()
    pp = db.query(PendingPayment).filter(PendingPayment.id == pending_id).first()
    if pp:
        pp.message_id = message_id
        db.commit()
    db.close()


def get_active_pending_payments() -> list[PendingPayment]:
    """Return all unfulfilled, non-expired pending payments."""
    db = SessionLocal()
    now = datetime.utcnow()
    results = (
        db.query(PendingPayment)
        .filter(
            PendingPayment.fulfilled == False,
            PendingPayment.expires_at > now,
        )
        .all()
    )
    db.close()
    return results


def get_expired_pending_payments() -> list[PendingPayment]:
    db = SessionLocal()
    now = datetime.utcnow()
    results = (
        db.query(PendingPayment)
        .filter(
            PendingPayment.fulfilled == False,
            PendingPayment.expires_at <= now,
        )
        .all()
    )
    db.close()
    return results


def mark_fulfilled(pending_id: int):
    db = SessionLocal()
    pp = db.query(PendingPayment).filter(PendingPayment.id == pending_id).first()
    if pp:
        pp.fulfilled = True
        db.commit()
    db.close()


def get_by_note(note: str) -> PendingPayment | None:
    db = SessionLocal()
    pp = db.query(PendingPayment).filter(PendingPayment.note == note).first()
    db.close()
    return pp
