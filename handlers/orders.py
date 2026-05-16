from telegram import Update
from telegram.ext import ContextTypes
from services.orders import get_user_orders
from handlers.start import t


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_id = str(user.id)
    orders  = get_user_orders(user_id)

    if not orders:
        await update.message.reply_text(t(context, "no_orders", user_id=user_id))
        return

    text = t(context, "orders_title", user_id=user_id)
    for o in orders:
        icon  = "✅" if o.status == "approved" else "❌" if o.status == "rejected" else "⏳"
        text += f"{icon} *#{o.id}* — {o.product_name}\n💵 ${o.price} | 📌 {o.status}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")
