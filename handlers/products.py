import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)
from services.orders import create_order, get_user_orders, update_order, get_order
from services.products import get_active_products
from services.keys import pop_key, count_available_keys
from services.binance_verify import verify_binance_transaction
from keyboards.menus import main_menu

# Conversation states
CHOOSE_PAYMENT, WAIT_TX_ID = range(2)


def build_products_keyboard():
    db_products = get_active_products()
    if not db_products:
        return None, "❌ No products available right now."
    keyboard = [
        [InlineKeyboardButton(
            f"{p.emoji} {p.name} | ${p.price}",
            callback_data=f"buy_{p.id}"
        )]
        for p in db_products
    ]
    keyboard.append([InlineKeyboardButton("🛟 Support",  callback_data="support")])
    keyboard.append([InlineKeyboardButton("⬅️ Back",    callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard), None


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup, error = build_products_keyboard()
    await update.message.reply_text(
        error if error else "🛒 Choose a product:",
        reply_markup=markup
    )


# ── Step 1: product selected → show Binance Pay details ──────────────────
async def on_buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("buy_", ""))
    db_products = get_active_products()
    product = next((p for p in db_products if p.id == product_id), None)

    if not product:
        await query.message.reply_text("❌ Product not found.")
        return ConversationHandler.END

    available = count_available_keys(product_id)
    if available == 0:
        await query.message.reply_text(
            f"⚠️ *{product.name}* is currently out of stock.\n"
            "Please try again later or contact support.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data["pending_product"] = {
        "id":    product.id,
        "name":  product.name,
        "price": product.price,
        "emoji": product.emoji,
    }

    binance_id = os.getenv("BINANCE_PAY_ID", "NOT SET")

    await query.message.edit_text(
        f"{product.emoji} *{product.name}*\n"
        f"💵 Price: *${product.price} USDT*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 *Pay via Binance Pay*\n\n"
        f"🆔 Binance Pay ID:\n`{binance_id}`\n\n"
        f"📌 Send exactly *${product.price} USDT*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 After payment, paste your *Binance Transaction ID* here:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel")
        ]])
    )
    return WAIT_TX_ID


# ── Step 2: user pastes TX ID → verify with Binance API ──────────────────
async def on_receive_tx_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_id   = update.message.text.strip()
    user    = update.effective_user
    product = context.user_data.get("pending_product")

    if not product:
        await update.message.reply_text("❌ Session expired. Please start again with /buy")
        return ConversationHandler.END

    order = create_order(
        telegram_id    = str(user.id),
        product_id     = product["id"],
        product_name   = product["name"],
        price          = product["price"],
        payment_method = "binance",
        tx_id          = tx_id,
    )

    wait_msg = await update.message.reply_text(
        "⏳ Verifying your payment with Binance...\nPlease wait.",
    )

    result = await verify_binance_transaction(tx_id, product["price"])

    if not result["success"]:
        update_order(order.id, status="rejected")
        await wait_msg.edit_text(
            f"❌ *Payment verification failed*\n\n"
            f"Reason: {result['error']}\n\n"
            "Please check your Transaction ID and try again, or contact support: @sookbit",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    key = pop_key(product["id"])

    if not key:
        update_order(order.id, status="approved")
        await wait_msg.edit_text(
            "✅ *Payment verified!*\n\n"
            "⚠️ We're processing your order manually. "
            "Your key will be sent shortly. Contact: @sookbit",
            parse_mode="Markdown"
        )
        await _notify_admin(update, order, product, tx_id, key=None)
        context.user_data.clear()
        return ConversationHandler.END

    update_order(order.id, status="approved", delivered_key=key)

    await wait_msg.edit_text(
        f"🎉 *Payment Verified & Order Confirmed!*\n\n"
        f"📦 {product['emoji']} *{product['name']}*\n"
        f"💵 ${product['price']} USDT\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔑 *Your Key/Code:*\n`{key}`\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Thank you for your purchase! 🙏\n"
        "For support: @sookbit",
        parse_mode="Markdown"
    )

    await _notify_admin(update, order, product, tx_id, key=key)
    context.user_data.clear()
    return ConversationHandler.END


async def _notify_admin(update, order, product, tx_id, key):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        return
    key_line = f"🔑 Key delivered: `{key}`" if key else "⚠️ No key available — send manually!"
    try:
        await update.get_bot().send_message(
            chat_id=admin_id,
            text=(
                f"{'✅' if key else '⚠️'} *Order #{order.id} {'Auto-Approved' if key else 'NEEDS KEY'}*\n\n"
                f"👤 @{update.effective_user.username or update.effective_user.first_name} "
                f"(`{update.effective_user.id}`)\n"
                f"📦 {product['emoji']} {product['name']} — ${product['price']}\n"
                f"🔖 TX ID: `{tx_id}`\n"
                f"{key_line}"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin notify error: {e}")


async def on_pay_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("❌ Order cancelled.", reply_markup=None)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow /start or /cancel to exit the conversation at any time."""
    context.user_data.clear()
    from handlers.start import start as start_handler
    await start_handler(update, context)
    return ConversationHandler.END


# ── Menu navigation callbacks ─────────────────────────────────────────────
async def product_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data == "back_main":
        await query.message.edit_text(
            f"🛒 Welcome back, {user.first_name}!\n\nChoose an option below 👇",
            reply_markup=main_menu()
        )
        return

    if data == "menu_products":
        markup, error = build_products_keyboard()
        await query.message.edit_text(
            error if error else "🛒 Choose a product:",
            reply_markup=markup
        )
        return

    if data == "menu_orders":
        orders = get_user_orders(str(user.id))
        if not orders:
            text = "📦 You have no orders yet."
        else:
            lines = []
            for o in orders:
                status_icon = "✅" if o.status == "approved" else "❌" if o.status == "rejected" else "⏳"
                lines.append(f"{status_icon} #{o.id} — {o.product_name} — ${o.price}")
            text = "📦 *Your orders:*\n\n" + "\n".join(lines)
        await query.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="back_main")
            ]])
        )
        return

    if data in ("menu_support", "support"):
        await query.message.edit_text(
            "🛟 Need help? Contact: @sookbit",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="back_main")
            ]])
        )
        return


# ── ConversationHandler export ────────────────────────────────────────────
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
    ],
    per_user=True,
    per_chat=True,
    per_message=False,
)
