from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.orders import get_user_orders
from handlers.start import t


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_id = str(user.id)
    orders  = get_user_orders(user_id)

    if not orders:
        text = t(context, "no_orders", user_id=user_id)
    else:
        text = t(context, "orders_title", user_id=user_id)
        for o in orders:
            icon  = "✅" if o.status == "approved" else "❌" if o.status == "rejected" else "⏳"
            text += f"{icon} *#{o.id}* — {o.product_name}\n💵 ${o.price} | 📌 {o.status}\n\n"

    back_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(context, "back_btn", user_id=user_id), callback_data="back_main")
    ]])

    # Handle both /orders command (message) and reply keyboard button (message)
    msg = update.message
    if msg:
        await msg.reply_text(text, parse_mode="Markdown", reply_markup=back_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text, parse_mode="Markdown", reply_markup=back_markup
        )
