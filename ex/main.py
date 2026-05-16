import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)
from dotenv import load_dotenv

from database import Base, engine

from handlers.start import start
from handlers.products import products, product_buttons, payment_conv_handler
from handlers.orders import my_orders
from handlers.admin import admin_orders, approve_order, reject_order

from admin.routes import router as admin_router

load_dotenv()

TOKEN      = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")   # e.g. https://prodseller.onrender.com

app = FastAPI()
app.include_router(admin_router)

telegram_app = Application.builder().token(TOKEN).build()

# ConversationHandler must be registered BEFORE the general CallbackQueryHandler
telegram_app.add_handler(payment_conv_handler)

telegram_app.add_handler(CommandHandler("start",       start))
telegram_app.add_handler(CommandHandler("produits",    products))
telegram_app.add_handler(CommandHandler("buy",         products))
telegram_app.add_handler(CommandHandler("acheter",     products))
telegram_app.add_handler(CommandHandler("orders",      my_orders))
telegram_app.add_handler(CommandHandler("adminorders", admin_orders))
telegram_app.add_handler(CommandHandler("approve",     approve_order))
telegram_app.add_handler(CommandHandler("reject",      reject_order))

# General callback handler for menu navigation (non-purchase buttons)
telegram_app.add_handler(CallbackQueryHandler(product_buttons))


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

    await telegram_app.initialize()
    await telegram_app.start()

    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
        await telegram_app.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
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
async def webhook(request: Request):
    data   = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/")
def home():
    return {"status": "running", "admin": "/admin"}
