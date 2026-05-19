"""
Binance Pay — C2C/Pay transfer listener.

Strategy:
  Binance Pay does NOT expose a "get transfers by remark" API.
  We use the Binance Spot Wallet API endpoint:
    GET /sapi/v1/capital/deposit/hisrec   (deposits from others to you)
  OR the Pay Trade History:
    GET /sapi/v1/pay/transactions          (Binance Pay send/receive)

  We poll /sapi/v1/pay/transactions?limit=100 every ~10 seconds.
  Each transaction has a "remark" or "note" field.
  When a transaction matches (note == pending_payment.note AND
  amount >= price AND orderType == "C2C"), we mark it fulfilled.

Docs:
  https://binance-docs.github.io/apidocs/spot/en/#get-pay-trade-history-user_data
"""
import os
import time
import hmac
import hashlib
import httpx
import asyncio
from datetime import datetime, timezone

BASE_URL = "https://api.binance.com"

_PLACEHOLDER = {"", "your_api_key", "your_secret_key", "YOUR_API_KEY", "YOUR_SECRET_KEY"}


def _keys():
    k = os.getenv("BINANCE_API_KEY", "").strip()
    s = os.getenv("BINANCE_SECRET_KEY", "").strip()
    return k, s


def _configured():
    k, s = _keys()
    return k not in _PLACEHOLDER and s not in _PLACEHOLDER


def _sign(params: str, secret: str) -> str:
    return hmac.new(secret.encode(), params.encode(), hashlib.sha256).hexdigest()


async def fetch_recent_pay_transactions(limit: int = 100) -> list[dict]:
    """
    Fetch recent Binance Pay transactions (incoming C2C transfers).
    Returns list of raw transaction dicts.
    """
    api_key, secret = _keys()
    if not _configured():
        return []

    ts = int(time.time() * 1000)
    params = f"limit={limit}&timestamp={ts}"
    signature = _sign(params, secret)
    url = f"{BASE_URL}/sapi/v1/pay/transactions?{params}&signature={signature}"

    headers = {"X-MBX-APIKEY": api_key}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
        data = resp.json()
        if data.get("status") == "SUCCESS" or isinstance(data.get("data"), list):
            return data.get("data", [])
        return []
    except Exception as e:
        print(f"[BinancePay] fetch error: {e}")
        return []


def match_note_in_transactions(transactions: list[dict], note: str, price: float) -> dict | None:
    """
    Search transactions for one matching note (remark) and amount >= price.
    Returns the matching tx dict or None.
    """
    note_upper = note.upper()
    for tx in transactions:
        # Binance Pay transaction fields (may vary by account type)
        remark = (
            tx.get("remark") or
            tx.get("note") or
            tx.get("memo") or
            tx.get("goodsName") or
            ""
        ).upper()

        order_type = tx.get("orderType", "")
        tx_status  = tx.get("transactionStatus", tx.get("status", ""))
        amount     = float(tx.get("transAmount") or tx.get("amount") or 0)
        currency   = (tx.get("currency") or tx.get("asset") or "USDT").upper()

        # Match: remark contains the note, paid enough, currency correct
        if (
            note_upper in remark and
            amount >= float(price) and
            currency == "USDT" and
            tx_status in ("SUCCESS", "COMPLETED", "PAID", "")
        ):
            return tx

    return None
