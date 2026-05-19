"""
Background polling loop — checks Binance Pay transactions every 12 seconds.
Runs as an asyncio task started at bot startup.

For each active PendingPayment:
  - Check if it appears in the last 100 Binance Pay transactions (matched by note)
  - If yes → deliver product, send success message, mark fulfilled
  - If expired → send expiry message, mark fulfilled
"""
import asyncio
import os
from datetime import datetime

from services.binance_pay import fetch_recent_pay_transactions, match_note_in_transactions
from services.pending_payments import (
    get_active_pending_payments,
    get_expired_pending_payments,
    mark_fulfilled,
)
from services.orders import create_order, deliver_key_for_order
from services.keys import pop_key
from services.products import get_all_products

POLL_INTERVAL = 12  # seconds between polls


async def _deliver(bot, pp, product, tx_ref: str):
    """Pop a key and deliver it to the user."""
    order = create_order(
        telegram_id    = pp.telegram_id,
        product_id     = pp.product_id,
        product_name   = product.name,
        price          = pp.price,
        payment_method = "binance_pay",
        tx_id          = tx_ref,
    )

    key = pop_key(pp.product_id)

    if key:
        deliver_key_for_order(order.id, key)
        text = (
            f"✅ *Deposit Request Created!*\n\n"
            f"🎉 *Order Confirmed!*\n\n"
            f"📦 {product.emoji} *{product.name}*\n"
            f"💵 ${pp.price} USDT\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔑 *Your Key:*\n`{key}`\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Thank you! 🙏 Support: @sookbit"
        )
    else:
        text = (
            f"✅ *Payment Received!*\n\n"
            f"📦 {product.emoji} *{product.name}* — ${pp.price} USDT\n\n"
            f"⚠️ Stock temporarily unavailable.\n"
            f"Contact support: @sookbit"
        )

    # Edit or send
    try:
        if pp.message_id:
            await bot.edit_message_text(
                chat_id    = pp.chat_id,
                message_id = pp.message_id,
                text       = text,
                parse_mode = "Markdown",
            )
        else:
            await bot.send_message(chat_id=pp.chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"[Poller] deliver message error: {e}")
        try:
            await bot.send_message(chat_id=pp.chat_id, text=text, parse_mode="Markdown")
        except Exception:
            pass

    # Notify admin
    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        key_line = f"🔑 Key: `{key}`" if key else "⚠️ No key — deliver manually!"
        try:
            await bot.send_message(
                chat_id    = admin_id,
                text       = (
                    f"{'✅' if key else '⚠️'} *Auto-Payment Confirmed*\n\n"
                    f"👤 Telegram ID: `{pp.telegram_id}`\n"
                    f"📦 {product.emoji} {product.name} — ${pp.price}\n"
                    f"🏷️ Note: `{pp.note}`\n"
                    f"🔖 TX ref: `{tx_ref}`\n"
                    f"{key_line}"
                ),
                parse_mode = "Markdown",
            )
        except Exception as e:
            print(f"[Poller] admin notify error: {e}")


async def _expire(bot, pp):
    """Send expiry message."""
    text = (
        "⏰ *Payment expired.*\n\n"
        "Your 30-minute payment window has closed.\n"
        "Start a new order if you still want to buy.\n\n"
        "Support: @sookbit"
    )
    try:
        if pp.message_id:
            await bot.edit_message_text(
                chat_id    = pp.chat_id,
                message_id = pp.message_id,
                text       = text,
                parse_mode = "Markdown",
            )
        else:
            await bot.send_message(chat_id=pp.chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"[Poller] expire message error: {e}")


async def payment_poll_loop(bot):
    """
    Infinite polling loop. Call with:
        asyncio.create_task(payment_poll_loop(telegram_app.bot))
    """
    print("✅ [Poller] Payment polling loop started")
    products_cache: dict = {}

    def _get_product(pid):
        if pid not in products_cache:
            for p in get_all_products():
                products_cache[p.id] = p
        return products_cache.get(pid)

    while True:
        try:
            # 1. Handle expired first (no API call needed)
            expired = get_expired_pending_payments()
            for pp in expired:
                mark_fulfilled(pp.id)
                await _expire(bot, pp)

            # 2. Fetch Binance Pay transactions once
            active = get_active_pending_payments()
            if active:
                txs = await fetch_recent_pay_transactions(limit=100)
                # Refresh product cache
                products_cache = {p.id: p for p in get_all_products()}

                for pp in active:
                    tx = match_note_in_transactions(txs, pp.note, pp.price)
                    if tx:
                        mark_fulfilled(pp.id)
                        tx_ref = (
                            tx.get("orderId") or
                            tx.get("transId") or
                            tx.get("bizId") or
                            pp.note
                        )
                        product = _get_product(pp.product_id)
                        if product:
                            await _deliver(bot, pp, product, tx_ref)

        except Exception as e:
            print(f"[Poller] loop error: {e}")

        await asyncio.sleep(POLL_INTERVAL)
