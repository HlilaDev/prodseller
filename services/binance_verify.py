"""
Binance Pay — verify a C2C/Pay transaction by order ID.
Docs: https://developers.binance.com/docs/binance-pay/api-order-query-v2
"""
import os
import time
import hmac
import hashlib
import random
import string
import httpx

BASE_URL = "https://bpay.binanceapi.com"

_PLACEHOLDER_VALUES = {"your_api_key", "your_secret_key", "", "YOUR_API_KEY", "YOUR_SECRET_KEY"}


def _get_keys():
    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    secret_key = os.getenv("BINANCE_SECRET_KEY", "").strip()
    return api_key, secret_key


def _keys_configured():
    api_key, secret_key = _get_keys()
    return (
        api_key    not in _PLACEHOLDER_VALUES and
        secret_key not in _PLACEHOLDER_VALUES
    )


def _nonce(n=32):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def _sign(payload: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha512
    ).hexdigest().upper()


async def verify_binance_transaction(tx_id: str, expected_amount: float) -> dict:
    """
    Query Binance Pay for a transaction by prepay ID / merchant trade no.
    Returns:
        {"success": True,  "amount": 3.0, "currency": "USDT", "status": "SUCCESS"}
        {"success": False, "error": "reason"}
    """
    # Read keys fresh at call time (not at module import time)
    api_key, secret_key = _get_keys()

    if not _keys_configured():
        return {"success": False, "error": "Binance API keys not configured"}

    timestamp  = str(int(time.time() * 1000))
    nonce_str  = _nonce()
    body       = '{"merchantTradeNo":"' + tx_id + '"}'
    payload    = f"{timestamp}\n{nonce_str}\n{body}\n"
    signature  = _sign(payload, secret_key)

    headers = {
        "Content-Type":              "application/json",
        "BinancePay-Timestamp":      timestamp,
        "BinancePay-Nonce":          nonce_str,
        "BinancePay-Certificate-SN": api_key,
        "BinancePay-Signature":      signature,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{BASE_URL}/binancepay/openapi/v2/order/query",
                headers=headers,
                content=body,
            )
        data = resp.json()

        if data.get("status") != "SUCCESS":
            return {"success": False, "error": data.get("errorMessage", "Query failed")}

        order_data   = data.get("data", {})
        order_status = order_data.get("status")          # SUCCESS / INITIAL / EXPIRED
        paid_amount  = float(order_data.get("orderAmount", 0))
        currency     = order_data.get("currency", "USDT")

        if order_status != "SUCCESS":
            return {"success": False, "error": f"Payment not completed (status: {order_status})"}

        if paid_amount < float(expected_amount):
            return {
                "success": False,
                "error": f"Amount mismatch: expected ${expected_amount}, got ${paid_amount} {currency}"
            }

        return {"success": True, "amount": paid_amount, "currency": currency, "status": order_status}

    except Exception as e:
        return {"success": False, "error": str(e)}
