from telegram import Update
from telegram.ext import ContextTypes
from services.orders import get_user_orders


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    orders = get_user_orders(user.id)

    if not orders:
        await update.message.reply_text(
            "📦 You have no orders yet."
        )
        return

    text = "📦 Your Orders:\n\n"

    for order in orders:
        text += (
            f"🧾 Order #{order.id}\n"
            f"📦 Product: {order.product_name}\n"
            f"💵 Price: ${order.price}\n"
            f"📌 Status: {order.status}\n\n"
        )

    await update.message.reply_text(text)