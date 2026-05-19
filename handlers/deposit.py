"""
Deposit handler — Binance Pay, USDT TRC20, USDT BEP20
"""
import os
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters,
)
from services.deposit import (
    NETWORKS, EXPIRY_SECONDS, get_network_address,
    create_deposit, get_deposit_by_ref, confirm_deposit,
)
from handlers.start import t as _t

SEL_NETWORK, ENTER_AMOUNT = range(10, 12)

MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "1.0"))


def network_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Binance Pay",  callback_data="net_binance_pay")],
        [
            InlineKeyboardButton("💎 USDT TRC20", callback_data="net_usdt_trc20"),
            InlineKeyboardButton("🟡 USDT BEP20", callback_data="net_usdt_bep20"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")],
    ])


async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "💳 *Select the network you will use to send your payment:*",
        parse_mode="Markdown",
        reply_markup=network_keyboard()
    )
    return SEL_NETWORK


async def on_network_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    net_key = query.data.replace("net_", "")
    context.user_data["deposit_network"] = net_key

    min_str = f"{MIN_DEPOSIT:.2f}".rstrip("0").rstrip(".")
    await query.message.edit_text(
        f"💰 *Enter the amount you want to deposit (USD):*\n\n"
        f"Example: `10` or `5.5`\n"
        f"Minimum: ${min_str}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")
        ]])
    )
    return ENTER_AMOUNT


async def on_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_id = str(user.id)
    text    = update.message.text.strip().replace(",", ".")

    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number like `10` or `5.5`.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")
            ]])
        )
        return ENTER_AMOUNT

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ Minimum deposit is *${MIN_DEPOSIT}* USDT.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")
            ]])
        )
        return ENTER_AMOUNT

    net_key = context.user_data.get("deposit_network", "binance_pay")
    net     = NETWORKS[net_key]
    address = get_network_address(net_key)
    deposit = create_deposit(user_id, amount, net_key)

    instruction = net["instructions"].format(address=address)
    minutes     = EXPIRY_SECONDS // 60

    msg = (
        f"✅ *Deposit Request Created!*\n\n"
        f"🔶 Method: *{net['label']}*\n\n"
        f"💰 Send EXACTLY:\n"
        f"`{amount}` USDT\n\n"
        f"🆔 {instruction}\n\n"
        f"⚠️ *IMPORTANT:*\n"
        f"To confirm your payment, you MUST do ONE of the following:\n"
        f"1️⃣ Write this Note / Remark when sending: `{deposit.order_ref}`\n"
        f"2️⃣ OR after paying, send the Order ID (Reference) here.\n\n"
        f"🤖 *Auto-detection:* Payments with the correct note are\n"
        f"detected in 1-2 mins automatically!\n"
        f"📩 Or manually verify by sending: `/claim {deposit.order_ref}`\n\n"
        f"⏰ This request expires in *{minutes} minutes*."
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel deposit", callback_data="dep_cancel")
        ]])
    )

    await _notify_admin_deposit(update, deposit, net, amount, address)
    asyncio.create_task(_watch_expiry(update, deposit.id, deposit.order_ref, user_id))
    return ENTER_AMOUNT


async def on_claim_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args    = context.args

    if not args:
        await update.message.reply_text(
            "Usage: `/claim ORDER_ID`\nExample: `/claim T0AB12CDEF`",
            parse_mode="Markdown"
        )
        return

    ref     = args[0].strip().upper()
    deposit = get_deposit_by_ref(ref)

    if not deposit:
        await update.message.reply_text("❌ Order ID not found.")
        return
    if deposit.telegram_id != user_id:
        await update.message.reply_text("❌ This order does not belong to you.")
        return
    if deposit.status == "confirmed":
        await update.message.reply_text("✅ This deposit was already confirmed!")
        return
    if deposit.status == "expired" or int(time.time()) > deposit.expires_at:
        await update.message.reply_text("⏰ This deposit request has expired.")
        return

    confirm_deposit(deposit.id, tx_id=ref)
    await update.message.reply_text(
        f"✅ *Claim submitted!*\n\n"
        f"Order `{ref}` sent to admin for verification.\n"
        f"You will be notified once confirmed.",
        parse_mode="Markdown"
    )

    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        try:
            await update.get_bot().send_message(
                chat_id=admin_id,
                text=(
                    f"📩 *Manual Claim Request*\n\n"
                    f"👤 @{update.effective_user.username or update.effective_user.first_name} "
                    f"(`{user_id}`)\n"
                    f"🔖 Order Ref: `{ref}`\n"
                    f"💰 Amount: ${deposit.amount} USDT\n"
                    f"🌐 Network: {deposit.network}\n\n"
                    f"Use `/confirm_deposit {ref}` to approve."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Admin notify error: {e}")


async def admin_confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = os.getenv("ADMIN_ID")
    if str(update.effective_user.id) != str(admin_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/confirm_deposit ORDER_REF`", parse_mode="Markdown")
        return

    ref     = args[0].strip().upper()
    deposit = get_deposit_by_ref(ref)

    if not deposit:
        await update.message.reply_text(f"❌ Deposit `{ref}` not found.", parse_mode="Markdown")
        return

    confirm_deposit(deposit.id)
    await update.message.reply_text(f"✅ Deposit `{ref}` confirmed!", parse_mode="Markdown")

    try:
        await update.get_bot().send_message(
            chat_id=deposit.telegram_id,
            text=(
                f"🎉 *Deposit Confirmed!*\n\n"
                f"💰 *${deposit.amount} USDT* has been added to your balance.\n"
                f"🔖 Order: `{ref}`\n\nThank you! 🙏"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"User notify error: {e}")


async def on_dep_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    for key in ("deposit_network", "deposit_id", "deposit_ref"):
        context.user_data.pop(key, None)
    await query.message.edit_text("❌ Deposit cancelled.", reply_markup=None)
    return ConversationHandler.END


async def _watch_expiry(update, deposit_id, ref, user_id):
    await asyncio.sleep(EXPIRY_SECONDS + 5)
    deposit = get_deposit_by_ref(ref)
    if deposit and deposit.status == "pending":
        try:
            await update.get_bot().send_message(
                chat_id=user_id,
                text=f"⏰ Your deposit request `{ref}` has *expired*.\nStart a new deposit anytime.",
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def _notify_admin_deposit(update, deposit, net, amount, address):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        return
    try:
        await update.get_bot().send_message(
            chat_id=admin_id,
            text=(
                f"💰 *New Deposit Request*\n\n"
                f"👤 @{update.effective_user.username or update.effective_user.first_name} "
                f"(`{update.effective_user.id}`)\n"
                f"🌐 Network: {net['label']}\n"
                f"💵 Amount: ${amount} USDT\n"
                f"🔖 Order Ref: `{deposit.order_ref}`\n\n"
                f"⏰ Expires in {EXPIRY_SECONDS//60} min.\n"
                f"Use `/confirm_deposit {deposit.order_ref}` to confirm manually."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin deposit notify error: {e}")


deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(deposit_start, pattern=r"^menu_deposit$")],
    states={
        SEL_NETWORK: [
            CallbackQueryHandler(on_network_selected, pattern=r"^net_"),
            CallbackQueryHandler(on_dep_cancel, pattern=r"^dep_cancel$"),
        ],
        ENTER_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, on_amount_entered),
            CallbackQueryHandler(on_dep_cancel, pattern=r"^dep_cancel$"),
        ],
    },
    fallbacks=[
        CommandHandler("start",  lambda u, c: ConversationHandler.END),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(on_dep_cancel, pattern=r"^dep_cancel$"),
    ],
    per_user=True,
    per_chat=True,
    per_message=False,
    block=False,
    allow_reentry=True,
)
