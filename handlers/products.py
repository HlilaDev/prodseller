import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters,
)
from services.orders import create_order, get_user_orders, update_order, deliver_key_for_order
from services.products import get_active_products
from services.keys import pop_key, count_available_keys
from services.binance_verify import verify_binance_transaction
from keyboards.menus import main_menu

CHOOSE_PAYMENT, WAIT_TX_ID = range(2)


def _t(context, key, user_id=None, **kwargs):
    from handlers.start import t
    return t(context, key, user_id=user_id, **kwargs)


def build_products_keyboard(context, user_id=None):
    db_products = get_active_products()
    if not db_products:
        return None, _t(context, "no_products", user_id=user_id)
    keyboard = [
        [InlineKeyboardButton(f"{p.emoji} {p.name} | ${p.price}", callback_data=f"buy_{p.id}")]
        for p in db_products
    ]
    keyboard.append([InlineKeyboardButton("🛟 Support", callback_data="support")])
    keyboard.append([InlineKeyboardButton(_t(context, "back_btn", user_id=user_id), callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard), None


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    markup, error = build_products_keyboard(context, str(user.id))
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        error if error else _t(context, "choose_product", user_id=str(user.id)),
        reply_markup=markup
    )


async def on_buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    product_id  = int(query.data.replace("buy_", ""))
    db_products = get_active_products()
    product     = next((p for p in db_products if p.id == product_id), None)

    if not product:
        await query.message.reply_text(_t(context, "product_not_found", user_id=user_id))
        return ConversationHandler.END

    if count_available_keys(product_id) == 0:
        await query.message.reply_text(
            _t(context, "out_of_stock", user_id=user_id, name=product.name),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data["pending_product"] = {
        "id": product.id, "name": product.name,
        "price": product.price, "emoji": product.emoji,
    }

    binance_id = os.getenv("BINANCE_PAY_ID", "NOT SET")
    await query.message.edit_text(
        _t(context, "pay_instructions", user_id=user_id,
           emoji=product.emoji, name=product.name,
           price=product.price, binance_id=binance_id),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(_t(context, "cancel_btn", user_id=user_id), callback_data="pay_cancel")
        ]])
    )
    return WAIT_TX_ID


async def on_receive_tx_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called when the client sends a Binance transaction ID.
    Flow:
      1. Create a pending order in the DB.
      2. Verify the TX via Binance Pay API.
      3. If verified → pop a key from product_keys → deliver automatically.
      4. If no key available → notify admin to deliver manually.
      5. If verification fails → mark order rejected + ask to retry (stay in WAIT_TX_ID).
    """
    tx_id   = update.message.text.strip()
    user    = update.effective_user
    user_id = str(user.id)
    product = context.user_data.get("pending_product")

    if not product:
        await update.message.reply_text(_t(context, "session_expired", user_id=user_id))
        return ConversationHandler.END

    # ── 1. Create order (pending) ─────────────────────────────────────────
    order = create_order(
        telegram_id    = user_id,
        product_id     = product["id"],
        product_name   = product["name"],
        price          = product["price"],
        payment_method = "binance",
        tx_id          = tx_id,
    )

    wait_msg = await update.message.reply_text(_t(context, "verifying", user_id=user_id))

    # ── 2. Verify payment with Binance ────────────────────────────────────
    result = await verify_binance_transaction(tx_id, product["price"])

    if not result["success"]:
        update_order(order.id, status="rejected")
        # ⚠️ DO NOT clear user_data or return END here.
        # Stay in WAIT_TX_ID so the client can retry with the correct TX ID.
        await wait_msg.edit_text(
            f"❌ *Verification failed*\n"
            f"Reason: {result['error']}\n\n"
            f"👆 Please send the correct Binance Transaction ID to try again, "
            f"or press ❌ Cancel below.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel")
            ]])
        )
        return WAIT_TX_ID  # ← key fix: stay in conversation, allow retry

    # ── 3. Payment verified → pop a key from the DB ───────────────────────
    key = pop_key(product["id"])

    if not key:
        # Payment valid but stock ran out between check and pop (race condition)
        update_order(order.id, status="approved")
        await wait_msg.edit_text(_t(context, "no_key", user_id=user_id), parse_mode="Markdown")
        await _notify_admin(update, order, product, tx_id, key=None)
        context.user_data.clear()
        return ConversationHandler.END

    # ── 4. Key found → mark delivered and send to client ──────────────────
    deliver_key_for_order(order.id, key)   # status=approved + delivered_key saved

    await wait_msg.edit_text(
        _t(context, "order_confirmed", user_id=user_id,
           emoji=product["emoji"], name=product["name"],
           price=product["price"], key=key),
        parse_mode="Markdown"
    )

    # ── 5. Notify admin ───────────────────────────────────────────────────
    await _notify_admin(update, order, product, tx_id, key=key)

    context.user_data.clear()
    return ConversationHandler.END


async def _notify_admin(update, order, product, tx_id, key):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        return
    key_line = f"🔑 Key: `{key}`" if key else "⚠️ No key in stock — send manually!"
    try:
        await update.get_bot().send_message(
            chat_id=admin_id,
            text=(
                f"{'✅' if key else '⚠️'} *Order #{order.id}*\n\n"
                f"👤 @{update.effective_user.username or update.effective_user.first_name} "
                f"(`{update.effective_user.id}`)\n"
                f"📦 {product['emoji']} {product['name']} — ${product['price']}\n"
                f"🔖 TX: `{tx_id}`\n{key_line}"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin notify error: {e}")


async def on_pay_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    await query.message.edit_text(_t(context, "order_cancelled", user_id=user_id), reply_markup=None)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    from handlers.start import start as start_handler
    await start_handler(update, context)
    return ConversationHandler.END


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


payment_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(on_buy_product, pattern=r"^buy_\d+$")],
    states={
        WAIT_TX_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, on_receive_tx_id),
            CallbackQueryHandler(on_pay_cancel, pattern="^pay_cancel$"),
        ],
    },
    fallbacks=[
        CommandHandler("start",  cancel_conversation),
        CommandHandler("cancel", cancel_conversation),
        CallbackQueryHandler(on_pay_cancel, pattern="^pay_cancel$"),
        # Menu buttons clicked during a purchase → cancel and go to menu
        CallbackQueryHandler(
            cancel_conversation,
            pattern=r"^(menu_products|menu_orders|menu_support|menu_language|back_main)$"
        ),
    ],
    per_user=True,
    per_chat=True,
    per_message=False,
    block=False,
    allow_reentry=True,
)
