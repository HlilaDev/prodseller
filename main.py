import os

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

from database import Base, engine

from handlers.start import start, language_callback
from handlers.products import products, product_buttons, payment_conv_handler
from handlers.orders import my_orders
from handlers.admin import admin_orders, approve_order, reject_order

from admin.routes import router as admin_router

load_dotenv()

TOKEN      = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")

app = FastAPI()
app.include_router(admin_router)

telegram_app = Application.builder().token(TOKEN).build()

# ── Handlers ──────────────────────────────────────────────────────────────

# 1. ConversationHandler FIRST
telegram_app.add_handler(payment_conv_handler)

# 2. Commands
telegram_app.add_handler(CommandHandler("start",       start))
telegram_app.add_handler(CommandHandler("produits",    products))
telegram_app.add_handler(CommandHandler("buy",         products))
telegram_app.add_handler(CommandHandler("acheter",     products))
telegram_app.add_handler(CommandHandler("orders",      my_orders))
telegram_app.add_handler(CommandHandler("adminorders", admin_orders))
telegram_app.add_handler(CommandHandler("approve",     approve_order))
telegram_app.add_handler(CommandHandler("reject",      reject_order))

# 3. Language callbacks
telegram_app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^(menu_language|setlang_.+)$"))

# 4. General inline callbacks
telegram_app.add_handler(CallbackQueryHandler(product_buttons))

# 5. Persistent Reply Keyboard — text button handler
async def handle_reply_buttons(update: Update, context):
    text = update.message.text
    if text in ("🛍️ Shop",):
        await products(update, context)
    elif text in ("📦 My Orders",):
        await my_orders(update, context)
    elif text in ("🛟 Support",):
        await update.message.reply_text("🛟 Need help? Contact: @sookbit")
    elif text in ("🌐 Language",):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English",  callback_data="setlang_en")],
            [InlineKeyboardButton("🇫🇷 Français", callback_data="setlang_fr")],
            [InlineKeyboardButton("🇸🇦 العربية",  callback_data="setlang_ar")],
        ]
        await update.message.reply_text(
            "🌐 Choose your language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

telegram_app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r"^(🛍️ Shop|📦 My Orders|🛟 Support|🌐 Language)$"),
    handle_reply_buttons
))


# ── FastAPI lifecycle ─────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    await telegram_app.initialize()
    await telegram_app.start()

    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        print(f"✅ Webhook set → {webhook_url}")
    else:
        print("⚠️  RENDER_URL not set — webhook not registered")


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
    data   = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/webhook")
async def webhook_get():
    return {"ok": True, "status": "webhook active"}


@app.get("/")
def home():
    return {"status": "running", "admin": "/admin"}
