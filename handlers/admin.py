import os
from telegram import Update
from telegram.ext import ContextTypes
from services.orders import get_all_orders, update_order_status, get_order

ADMIN_ID = os.getenv("ADMIN_ID")

PAYMENT_LABELS = {
    "binance": "Binance Pay 🟡",
    "bybit":   "Bybit 🔵",
    "usdt":    "USDT TRC20 🟢",
}


def _is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    orders = get_all_orders()
    if not orders:
        await update.message.reply_text("No orders found.")
        return

    text = "🛒 *Pending Orders:*\n\n"
    for o in orders[:20]:
        method = PAYMENT_LABELS.get(o.payment_method, o.payment_method or "—")
        tx     = o.tx_id or "—"
        text  += (
            f"#{o.id} | {o.product_name} | ${o.price}\n"
            f"   💳 {method} | TX: `{tx}` | {o.status}\n\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve ORDER_ID")
        return

    order_id = int(context.args[0])
    order    = update_order_status(order_id, "approved")

    if not order:
        await update.message.reply_text("❌ Order not found.")
        return

    await update.message.reply_text(f"✅ Order #{order.id} approved.")

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=order.telegram_id,
            text=(
                f"🎉 *Order #{order.id} Confirmed!*\n\n"
                f"📦 {order.product_name}\n"
                f"💵 ${order.price} USDT\n\n"
                "Your payment has been verified. Thank you! 🙏"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Could not notify user: {e}")


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /reject ORDER_ID")
        return

    order_id = int(context.args[0])
    order    = update_order_status(order_id, "rejected")

    if not order:
        await update.message.reply_text("❌ Order not found.")
        return

    await update.message.reply_text(f"❌ Order #{order.id} rejected.")

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=order.telegram_id,
            text=(
                f"❌ *Order #{order.id} Rejected*\n\n"
                f"📦 {order.product_name}\n\n"
                "Payment could not be verified. Please contact support: @sookbit"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Could not notify user: {e}")
