import os
import traceback

print("🔄 [1] Starting imports...")

try:
    from fastapi import FastAPI, Request
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
    )
    from dotenv import load_dotenv
    print("✅ [2] Core imports OK")
except Exception as e:
    print(f"❌ [2] Core import failed: {e}")
    traceback.print_exc()
    raise

try:
    from database import Base, engine, run_migrations
    print("✅ [3] Database import OK")
except Exception as e:
    print(f"❌ [3] Database import failed: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.start import start, language_callback
    print("✅ [4] start handler OK")
except Exception as e:
    print(f"❌ [4] start handler failed: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.products import products, product_buttons, payment_conv_handler
    print("✅ [5] products handler OK")
except Exception as e:
    print(f"❌ [5] products handler failed: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.orders import my_orders
    print("✅ [6] orders handler OK")
except Exception as e:
    print(f"❌ [6] orders handler failed: {e}")
    traceback.print_exc()
    raise

try:
    from handlers.admin import admin_orders, approve_order, reject_order
    print("✅ [7] admin handler OK")
except Exception as e:
    print(f"❌ [7] admin handler failed: {e}")
    traceback.print_exc()
    raise

try:
    from admin.routes import router as admin_router
    print("✅ [8] admin routes OK")
except Exception as e:
    print(f"❌ [8] admin routes failed: {e}")
    traceback.print_exc()
    raise

load_dotenv()

TOKEN      = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")

print(f"🔄 [9] TOKEN set: {'YES' if TOKEN else 'NO'}")
print(f"🔄 [9] RENDER_URL: {RENDER_URL or 'NOT SET'}")

app = FastAPI()
app.include_router(admin_router)

telegram_app = Application.builder().token(TOKEN).build()

# 1. ConversationHandler FIRST
telegram_app.add_handler(payment_conv_handler)
# 2. Commands
telegram_app.add_handler(CommandHandler("start",       start))
telegram_app.add_handler(CommandHandler("buy",         products))
telegram_app.add_handler(CommandHandler("orders",      my_orders))
telegram_app.add_handler(CommandHandler("adminorders", admin_orders))
telegram_app.add_handler(CommandHandler("approve",     approve_order))
telegram_app.add_handler(CommandHandler("reject",      reject_order))
# 3. Language callbacks
telegram_app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^(menu_language|setlang_.+)$"))
# 4. General inline callbacks
telegram_app.add_handler(CallbackQueryHandler(product_buttons))
# 5. Reply keyboard buttons
async def handle_reply_buttons(update: Update, context):
    text = update.message.text
    from handlers.start import t
    uid  = str(update.effective_user.id)
    if "Shop" in text or "متجر" in text or "Tienda" in text:
        await products(update, context)
    elif "Orders" in text or "طلبات" in text or "Pedidos" in text:
        await my_orders(update, context)
    elif "Support" in text or "دعم" in text or "Soporte" in text:
        await update.message.reply_text(t(context, "support_msg", user_id=uid))
    elif "Language" in text or "لغة" in text or "Idioma" in text:
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")],
        ]
        await update.message.reply_text(
            t(context, "choose_lang", user_id=uid),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))

print("✅ [10] All handlers registered")


@app.on_event("startup")
async def startup():
    print("🔄 [startup] Creating DB tables...")
    Base.metadata.create_all(bind=engine)
    run_migrations()
    print("✅ [startup] DB ready")

    print("🔄 [startup] Initializing Telegram app...")
    await telegram_app.initialize()
    await telegram_app.start()
    print("✅ [startup] Telegram app started")

    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        print(f"✅ [startup] Webhook set → {webhook_url}")
    else:
        print("⚠️  [startup] RENDER_URL not set — webhook not registered")


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
        import traceback
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
    return {"ok": True}


@app.get("/webhook")
async def webhook_get():
    return {"ok": True, "status": "webhook active"}


@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "running", "admin": "/admin"}
