import asyncio
import threading
import os

from fastapi import FastAPI, Request
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

TOKEN = os.getenv("BOT_TOKEN")

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


def _is_main_worker() -> bool:
    return os.environ.get("RUN_MAIN") != "false"


_bot_thread: threading.Thread | None = None


def _run_polling():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("✅ Bot polling started")
        telegram_app.run_polling(drop_pending_updates=True, close_loop=False)
    except Exception as e:
        print(f"⚠️  Polling error: {e}")
    finally:
        loop.close()


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

    global _bot_thread
    if not _is_main_worker():
        print("⏭️  Reloader parent — skipping bot polling")
        return
    if _bot_thread and _bot_thread.is_alive():
        print("⚠️  Polling thread already running")
        return

    try:
        _bot_thread = threading.Thread(target=_run_polling, daemon=True, name="bot-polling")
        _bot_thread.start()
    except Exception as e:
        print(f"⚠️  Bot failed to start: {e}")


@app.on_event("shutdown")
async def shutdown():
    try:
        if telegram_app.running:
            await telegram_app.stop()
            await telegram_app.shutdown()
    except Exception:
        pass
    print("🛑 Bot stopped")


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/")
def home():
    return {"status": "running", "admin": "/admin"}
