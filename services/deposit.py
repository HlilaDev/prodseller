"""
Deposit-based payment service.
Supports: Binance Pay, USDT TRC20, USDT BEP20
"""
import os
import random
import string
import time
from database import SessionLocal
from models import Deposit

NETWORKS = {
    "binance_pay": {
        "label": "💎 Binance Pay",
        "instructions": "Send to Binance Pay ID:\n`{address}`\n\n📌 Route: *Binance → Pay → Send → paste ID → enter amount*",
        "address_env": "BINANCE_PAY_ID",
    },
    "usdt_trc20": {
        "label": "💎 USDT TRC20",
        "instructions": "Send to TRC20 address:\n`{address}`",
        "address_env": "WALLET_TRC20",
    },
    "usdt_bep20": {
        "label": "🟡 USDT BEP20",
        "instructions": "Send to BEP20 address:\n`{address}`",
        "address_env": "WALLET_BEP20",
    },
}

EXPIRY_SECONDS = 30 * 60  # 30 minutes


def generate_order_ref(n=10):
    chars = string.ascii_uppercase + string.digits
    return "T" + "".join(random.choices(chars, k=n - 1))


def get_network_address(network_key: str) -> str:
    env = NETWORKS[network_key]["address_env"]
    return os.getenv(env, "NOT_SET")


def create_deposit(telegram_id: str, amount: float, network: str) -> "Deposit":
    db = SessionLocal()
    ref = generate_order_ref()
    deposit = Deposit(
        telegram_id=str(telegram_id),
        amount=amount,
        network=network,
        order_ref=ref,
        status="pending",
        expires_at=int(time.time()) + EXPIRY_SECONDS,
    )
    db.add(deposit)
    db.commit()
    db.refresh(deposit)
    db.close()
    return deposit


def get_deposit_by_ref(ref: str) -> "Deposit | None":
    db = SessionLocal()
    d = db.query(Deposit).filter(Deposit.order_ref == ref).first()
    db.close()
    return d


def confirm_deposit(deposit_id: int, tx_id: str = None) -> bool:
    db = SessionLocal()
    d = db.query(Deposit).filter(Deposit.id == deposit_id).first()
    if not d:
        db.close()
        return False
    d.status = "confirmed"
    if tx_id:
        d.tx_id = tx_id
    db.commit()
    db.close()
    return True
