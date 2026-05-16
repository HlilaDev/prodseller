from telegram import Update
from telegram.ext import ContextTypes
from services.orders import get_user_orders
from handlers.start import t


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    orders = get_user_orders(str(user.id))

    if not orders:
        await update.message.reply_text(t(context, "no_orders"))
        return

    text = t(context, "orders_title")
    for order in orders:
        icon   = "✅" if order.status == "approved" else "❌" if order.status == "rejected" else "⏳"
        text  += (
            f"{icon} *#{order.id}* — {order.product_name}\n"
            f"💵 ${order.price} | 📌 {order.status}\n\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")
