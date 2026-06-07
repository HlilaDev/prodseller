import os
import traceback

print("🔄 [1] Starting imports...")

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import FileResponse
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        MessageHandler, filters,
    )
    from dotenv import load_dotenv
    print("✅ [2] Core imports OK")
except Exception as e:
    print(f"❌ [2] Core import FAILED: {e}")
    traceback.print_exc()
    raise

try:
    from database import Base, engine, run_migrations
    import models  # noqa: registers all ORM models (including PendingPayment)
    print("✅ [3] Database OK")
except Exception as e:
    print(f"❌ [3] Database FAILED: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.start import start, language_callback
    from handlers.products import (
        products, product_buttons,
        on_buy_product, on_pay_cancel, on_claim, on_qty_selected,
    )
    from handlers.orders import my_orders
    from handlers.admin import admin_orders, approve_order, reject_order
    from admin.routes import router as admin_router
    from admin.api import api_router
    print("✅ [4] All handlers OK")
except Exception as e:
    print(f"❌ [4] Handler import FAILED: {e}")
    traceback.print_exc()
    raise

load_dotenv()
TOKEN      = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")
print(f"🔄 TOKEN={'YES' if TOKEN else 'NO'} | RENDER_URL={RENDER_URL or 'NOT SET'}")

app = FastAPI()
app.include_router(admin_router)
app.include_router(api_router)

@app.get("/admin/react")
async def react_dashboard():
    return FileResponse("dashboard.html")

telegram_app = Application.builder().token(TOKEN).build()

# ── Register handlers — ORDER MATTERS ────────────────────────────────────

# 1. Buy a product → quantity selector
telegram_app.add_handler(CallbackQueryHandler(on_buy_product, pattern=r"^buy_\d+$"))

# 2. Quantity selected → create pending payment
telegram_app.add_handler(CallbackQueryHandler(on_qty_selected, pattern=r"^qty_\d+_\d+$"))

# 3. Cancel deposit (pay_cancel_<id>)
telegram_app.add_handler(CallbackQueryHandler(on_pay_cancel, pattern=r"^pay_cancel_"))

# 4. Commands
telegram_app.add_handler(CommandHandler("start",       start))
telegram_app.add_handler(CommandHandler("buy",         products))
telegram_app.add_handler(CommandHandler("orders",      my_orders))
telegram_app.add_handler(CommandHandler("claim",       on_claim))
telegram_app.add_handler(CommandHandler("adminorders", admin_orders))
telegram_app.add_handler(CommandHandler("approve",     approve_order))
telegram_app.add_handler(CommandHandler("reject",      reject_order))

# 5. Language callbacks
telegram_app.add_handler(CallbackQueryHandler(
    language_callback, pattern=r"^(menu_language|setlang_.+)$"
))

# 6. General menu callbacks
telegram_app.add_handler(CallbackQueryHandler(product_buttons))

# 7. Reply keyboard buttons with 2-second cooldown
import time
_last_reply: dict = {}

async def handle_reply_buttons(update: Update, context):
    if not update.message or not update.message.text:
        return
    text       = update.message.text.strip()
    user_id    = str(update.effective_user.id)
    text_lower = text.lower()
    matched    = any(w in text_lower for w in ("shop", "order", "support", "language", "lang"))
    if not matched:
        return
    now = time.time()
    if now - _last_reply.get(user_id, 0) < 2:
        return
    _last_reply[user_id] = now
    from handlers.start import t
    if "shop" in text_lower:
        await products(update, context)
    elif "order" in text_lower:
        await my_orders(update, context)
    elif "support" in text_lower:
        await update.message.reply_text(t(context, "support_msg", user_id=user_id))
    elif "language" in text_lower or "lang" in text_lower:
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar")],
            [InlineKeyboardButton("🇪🇸 Español",  callback_data="setlang_es")],
        ]
        await update.message.reply_text(
            t(context, "choose_lang", user_id=user_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons),
    group=1
)

print("✅ [5] All handlers registered")


# ── FastAPI lifecycle ─────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    import asyncio
    from services.payment_poller import payment_poll_loop

    print("🔄 [startup] Creating DB tables...")
    try:
        Base.metadata.create_all(bind=engine)
        run_migrations()
        print("✅ [startup] DB ready")
    except Exception as e:
        print(f"❌ [startup] DB error: {e}")
        traceback.print_exc()

    print("🔄 [startup] Clearing old webhook...")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(
                f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"
            )
        print("✅ [startup] Old webhook cleared")
    except Exception as e:
        print(f"⚠️ [startup] Could not clear webhook: {e}")

    await asyncio.sleep(1)

    print("🔄 [startup] Starting Telegram app...")
    try:
        await telegram_app.initialize()
        await telegram_app.start()
        print("✅ [startup] Telegram app started")
    except Exception as e:
        print(f"❌ [startup] Telegram start error: {e}")
        traceback.print_exc()
        return

    if RENDER_URL:
        try:
            webhook_url = f"{RENDER_URL}/webhook"
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
            )
            print(f"✅ [startup] Webhook set → {webhook_url}")
        except Exception as e:
            print(f"❌ [startup] Webhook error: {e}")
    else:
        print("⚠️ RENDER_URL not set — webhook NOT configured")

    asyncio.create_task(payment_poll_loop(telegram_app.bot))
    print("✅ [startup] Payment polling task started")


@app.on_event("shutdown")
async def shutdown():
    print("🔄 [shutdown] Stopping bot...")
    try:
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    try:
        await telegram_app.stop()
        await telegram_app.shutdown()
    except Exception:
        pass
    print("🛑 Bot stopped")


@app.post("/webhook")
async def webhook_post(request: Request):
    try:
        data   = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
    return {"ok": True}


@app.get("/webhook")
async def webhook_get():
    return {"ok": True, "status": "webhook active"}


@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "running", "admin": "/admin", "dashboard": "/admin/react"}
