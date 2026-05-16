import os
import traceback

print("🔄 [1] Starting imports...")

try:
    from fastapi import FastAPI, Request
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
    print("✅ [3] Database OK")
except Exception as e:
    print(f"❌ [3] Database FAILED: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.start import start, language_callback
    from handlers.products import products, product_buttons, payment_conv_handler
    from handlers.orders import my_orders
    from handlers.admin import admin_orders, approve_order, reject_order
    from admin.routes import router as admin_router
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

telegram_app = Application.builder().token(TOKEN).build()

# ── IMPORTANT: Order matters ──────────────────────────────────────────────
# 1. ConversationHandler FIRST — it captures TX ID messages
telegram_app.add_handler(payment_conv_handler)

# 2. Commands
telegram_app.add_handler(CommandHandler("start",       start))
telegram_app.add_handler(CommandHandler("buy",         products))
telegram_app.add_handler(CommandHandler("orders",      my_orders))
telegram_app.add_handler(CommandHandler("adminorders", admin_orders))
telegram_app.add_handler(CommandHandler("approve",     approve_order))
telegram_app.add_handler(CommandHandler("reject",      reject_order))

# 3. Language callbacks
telegram_app.add_handler(CallbackQueryHandler(
    language_callback, pattern=r"^(menu_language|setlang_.+)$"
))

# 4. General inline callbacks (menu navigation)
telegram_app.add_handler(CallbackQueryHandler(product_buttons))

# 5. Reply keyboard buttons — strict matching + cooldown to prevent spam
import time

_last_reply: dict = {}  # user_id → timestamp

KNOWN_BUTTONS = [
    "🛍️ Shop", "📦 My Orders", "🛟 Support", "🌐 Language",
]

async def handle_reply_buttons(update: Update, context):
    if not update.message or not update.message.text:
        return

    text    = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # Only handle known reply keyboard buttons — ignore everything else
    if text not in KNOWN_BUTTONS:
        return

    # Cooldown: ignore if same user clicked within 2 seconds
    now = time.time()
    if now - _last_reply.get(user_id, 0) < 2:
        return
    _last_reply[user_id] = now

    from handlers.start import t

    if "Shop" in text:
        await products(update, context)
    elif "Orders" in text:
        await my_orders(update, context)
    elif "Support" in text:
        await update.message.reply_text(t(context, "support_msg", user_id=user_id))
    elif "Language" in text:
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")],
        ]
        await update.message.reply_text(
            t(context, "choose_lang", user_id=user_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

telegram_app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_reply_buttons
), group=1)

print("✅ [5] All handlers registered")


# ── FastAPI lifecycle ─────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    print("🔄 [startup] Creating DB tables...")
    try:
        Base.metadata.create_all(bind=engine)
        run_migrations()
        print("✅ [startup] DB ready")
    except Exception as e:
        print(f"❌ [startup] DB error: {e}")
        traceback.print_exc()

    print("🔄 [startup] Starting Telegram app...")
    try:
        await telegram_app.initialize()
        await telegram_app.start()
        print("✅ [startup] Telegram app started")
    except Exception as e:
        print(f"❌ [startup] Telegram start error: {e}")
        traceback.print_exc()

    if RENDER_URL:
        try:
            webhook_url = f"{RENDER_URL}/webhook"
            await telegram_app.bot.set_webhook(
                url=webhook_url, drop_pending_updates=True
            )
            print(f"✅ [startup] Webhook set → {webhook_url}")
        except Exception as e:
            print(f"❌ [startup] Webhook error: {e}")
    else:
        print("⚠️ RENDER_URL not set")


@app.on_event("shutdown")
async def shutdown():
    try:
        await telegram_app.bot.delete_webhook()
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
    return {"status": "running", "admin": "/admin"}
