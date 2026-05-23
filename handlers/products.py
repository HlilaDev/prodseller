import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services.orders import get_user_orders, create_order, deliver_key_for_order
from services.products import get_active_products
from services.keys import pop_key, count_available_keys
from services.pending_payments import create_pending_payment, update_message_id
from keyboards.menus import main_menu

BINANCE_PAY_ID = os.getenv("BINANCE_PAY_ID", "NOT_SET")
EXPIRE_MINUTES = 30


def _t(context, key, user_id=None, **kwargs):
    from handlers.start import t
    return t(context, key, user_id=user_id, **kwargs)


def build_products_keyboard(context, user_id=None):
    db_products = get_active_products()
    if not db_products:
        return None, _t(context, "no_products", user_id=user_id)
    keyboard = []
    for p in db_products:
        qty = count_available_keys(p.id)
        qty_label = f"[{qty}]" if qty > 0 else "[❌ Out of stock]"
        keyboard.append([
            InlineKeyboardButton(
                f"{p.emoji} {p.name} | ${p.price} {qty_label}",
                callback_data=f"buy_{p.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🛟 Support", callback_data="support")])
    keyboard.append([InlineKeyboardButton(_t(context, "back_btn", user_id=user_id), callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard), None


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    markup, error = build_products_keyboard(context, str(user.id))
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        error if error else _t(context, "choose_product", user_id=str(user.id)),
        reply_markup=markup
    )


def _build_payment_message(product, note: str, price: float) -> str:
    return (
        f"✅ *Deposit Request Created!*\n\n"
        f"🔸 *Method:* Binance Pay\n\n"
        f"💰 *Send EXACTLY:*\n"
        f"`{price}` USDT\n\n"
        f"🆔 *To Binance ID:*\n"
        f"`{BINANCE_PAY_ID}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *IMPORTANT:*\n"
        f"To confirm your payment, you MUST do ONE of the following:\n\n"
        f"1️⃣ Write this *Note / Remark* when sending:\n"
        f"`{note}`\n\n"
        f"2️⃣ OR after paying, send the Order ID here:\n"
        f"`/claim {note}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📱 *Binance → Pay → Send → paste ID → enter amount*\n\n"
        f"🤖 *Auto-detection:* Payments with the correct note are "
        f"detected in 1-2 mins automatically!\n\n"
        f"⏰ This request expires in *{EXPIRE_MINUTES} minutes.*"
    )


# ── Buy button → show deposit window (NO ConversationHandler) ─────────────
async def on_buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    product_id  = int(query.data.replace("buy_", ""))
    db_products = get_active_products()
    product     = next((p for p in db_products if p.id == product_id), None)

    if not product:
        await query.message.reply_text(_t(context, "product_not_found", user_id=user_id))
        return

    if count_available_keys(product_id) == 0:
        await query.message.reply_text(
            _t(context, "out_of_stock", user_id=user_id, name=product.name),
            parse_mode="Markdown"
        )
        return

    chat_id = str(query.message.chat_id)
    pp = create_pending_payment(
        telegram_id = user_id,
        product_id  = product_id,
        price       = product.price,
        chat_id     = chat_id,
    )

    text = _build_payment_message(product, pp.note, pp.price)

    sent = await query.message.edit_text(
        text,
        parse_mode   = "Markdown",
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data=f"pay_cancel_{pp.id}"),
        ]])
    )

    update_message_id(pp.id, sent.message_id)


# ── Cancel deposit button ─────────────────────────────────────────────────
async def on_pay_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    data = query.data  # "pay_cancel_<id>"
    pending_id = None
    try:
        pending_id = int(data.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        pass

    if pending_id:
        from services.pending_payments import mark_fulfilled
        mark_fulfilled(pending_id)

    # Show main menu again so nothing is blocked
    from handlers.start import t
    try:
        await query.message.edit_text(
            t(context, "welcome_back", user_id=user_id, name=query.from_user.first_name),
            reply_markup=main_menu(),
        )
    except Exception:
        await query.message.reply_text(
            t(context, "welcome_back", user_id=user_id, name=query.from_user.first_name),
            reply_markup=main_menu(),
        )


# ── /claim NOTE — manual payment verification ─────────────────────────────
async def on_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/claim YOUR_NOTE`", parse_mode="Markdown")
        return

    note = args[0].upper()

    from services.pending_payments import get_by_note, mark_fulfilled
    from services.binance_pay import fetch_recent_pay_transactions, match_note_in_transactions
    from services.products import get_all_products
    from services.keys import pop_key
    from services.orders import create_order, deliver_key_for_order

    pp = get_by_note(note)

    if not pp:
        await update.message.reply_text("❌ No pending payment found with this note.")
        return
    if pp.fulfilled:
        await update.message.reply_text("✅ This payment was already processed.")
        return
    if pp.telegram_id != user_id:
        await update.message.reply_text("❌ This note doesn't belong to your account.")
        return
    if pp.expires_at < datetime.utcnow():
        mark_fulfilled(pp.id)
        await update.message.reply_text("⏰ This payment request has expired. Please start a new order.")
        return

    wait = await update.message.reply_text("⏳ Checking Binance Pay... please wait.")

    txs = await fetch_recent_pay_transactions(limit=100)
    tx  = match_note_in_transactions(txs, pp.note, pp.price)

    if not tx:
        await wait.edit_text(
            "❌ *Payment not found yet.*\n\n"
            "Make sure you:\n"
            "• Sent the correct amount\n"
            "• Added the note in the Remark field\n"
            "• Payment completed successfully\n\n"
            "Auto-detection runs every 12 seconds. Try again in 1-2 min.",
            parse_mode="Markdown"
        )
        return

    mark_fulfilled(pp.id)
    tx_ref = tx.get("orderId") or tx.get("transId") or tx.get("bizId") or pp.note

    products_map = {p.id: p for p in get_all_products()}
    product = products_map.get(pp.product_id)

    if not product:
        await wait.edit_text("✅ Payment confirmed! Contact support for delivery.")
        return

    order = create_order(
        telegram_id    = user_id,
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
            f"⚠️ Stock temporarily unavailable. Contact support: @sookbit"
        )

    await wait.edit_text(text, parse_mode="Markdown")

    if pp.message_id and pp.chat_id:
        try:
            await update.get_bot().edit_message_text(
                chat_id=pp.chat_id, message_id=pp.message_id,
                text=text, parse_mode="Markdown",
            )
        except Exception:
            pass

    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        key_line = f"🔑 Key: `{key}`" if key else "⚠️ No key — deliver manually!"
        try:
            await update.get_bot().send_message(
                chat_id    = admin_id,
                text       = (
                    f"{'✅' if key else '⚠️'} *Manual Claim Confirmed*\n\n"
                    f"👤 `{user_id}`\n"
                    f"📦 {product.emoji} {product.name} — ${pp.price}\n"
                    f"🏷️ Note: `{pp.note}`\n"
                    f"🔖 TX: `{tx_ref}`\n"
                    f"{key_line}"
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass


# ── General menu button router ────────────────────────────────────────────
async def product_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    user_id = str(user.id)
    data    = query.data

    if data == "back_main":
        await query.message.edit_text(
            _t(context, "welcome_back", user_id=user_id, name=user.first_name),
            reply_markup=main_menu()
        )
        return

    if data == "menu_products":
        markup, error = build_products_keyboard(context, user_id)
        await query.message.edit_text(
            error if error else _t(context, "choose_product", user_id=user_id),
            reply_markup=markup
        )
        return

    if data == "menu_orders":
        orders = get_user_orders(user_id)
        if not orders:
            text = _t(context, "no_orders", user_id=user_id)
        else:
            lines = []
            for o in orders:
                icon = "✅" if o.status == "approved" else "❌" if o.status == "rejected" else "⏳"
                lines.append(f"{icon} #{o.id} — {o.product_name} — ${o.price}")
            text = _t(context, "orders_title", user_id=user_id) + "\n".join(lines)
        await query.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t(context, "back_btn", user_id=user_id), callback_data="back_main")
            ]])
        )
        return

    if data in ("menu_support", "support"):
        await query.message.edit_text(
            _t(context, "support_msg", user_id=user_id),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_t(context, "back_btn", user_id=user_id), callback_data="back_main")
            ]])
        )
        return


# ── Stub so main.py import still works (no ConversationHandler used) ──────
payment_conv_handler = None
