import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.clients import create_client, set_client_lang, get_client_lang
from keyboards.menus import main_menu, persistent_menu

STORE_NAME = os.getenv("STORE_NAME", "ProdSeller Store")

TEXTS = {
    "en": {
        "greeting":          "☀️ Hello, {name}!\n\n🛒 Welcome to *{store}*\n\nChoose an option below 👇",
        "language_set":      "✅ Language set to *English*.",
        "choose_lang":       "🌐 Choose your language:",
        "choose_product":    "🛒 Choose a product:",
        "no_products":       "❌ No products available right now.",
        "out_of_stock":      "⚠️ *{name}* is out of stock.\nContact support.",
        "pay_instructions":  "{emoji} *{name}*\n💵 Price: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *Pay via Binance Pay*\n\n🆔 Binance Pay ID:\n`{binance_id}`\n\n📌 Send exactly *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n👇 Paste your *Binance Transaction ID* here:",
        "cancel_btn":        "❌ Cancel",
        "verifying":         "⏳ Verifying your payment...\nPlease wait.",
        "verify_failed":     "❌ *Payment verification failed*\n\nReason: {reason}\n\nContact support: @sookbit",
        "no_key":            "✅ *Payment verified!*\n\n⚠️ Processing manually.\nContact: @sookbit",
        "order_confirmed":   "🎉 *Order Confirmed!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *Your Key:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\nThank you! 🙏 Support: @sookbit",
        "order_cancelled":   "❌ Order cancelled.",
        "session_expired":   "❌ Session expired. Please start again.",
        "no_orders":         "📦 You have no orders yet.",
        "orders_title":      "📦 *Your orders:*\n\n",
        "support_msg":       "🛟 Need help? Contact: @sookbit",
        "back_btn":          "⬅️ Back",
        "welcome_back":      "🛒 Welcome back, {name}!\n\nChoose an option 👇",
        "product_not_found": "❌ Product not found.",
    },
    "ar": {
        "greeting":          "☀️ مرحباً، {name}!\n\n🛒 أهلاً بك في *{store}*\n\nاختر خياراً 👇",
        "language_set":      "✅ تم تعيين اللغة إلى *العربية*.",
        "choose_lang":       "🌐 اختر لغتك:",
        "choose_product":    "🛒 اختر منتجاً:",
        "no_products":       "❌ لا توجد منتجات متاحة حالياً.",
        "out_of_stock":      "⚠️ *{name}* غير متوفر.\nتواصل مع الدعم.",
        "pay_instructions":  "{emoji} *{name}*\n💵 السعر: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *الدفع عبر Binance Pay*\n\n🆔 معرّف Binance Pay:\n`{binance_id}`\n\n📌 أرسل *${price} USDT* بالضبط\n\n━━━━━━━━━━━━━━━━━━\n👇 أرسل *رقم معاملة Binance* هنا:",
        "cancel_btn":        "❌ إلغاء",
        "verifying":         "⏳ جارٍ التحقق من دفعتك...\nيرجى الانتظار.",
        "verify_failed":     "❌ *فشل التحقق من الدفع*\n\nالسبب: {reason}\n\nتواصل مع الدعم: @sookbit",
        "no_key":            "✅ *تم التحقق من الدفع!*\n\n⚠️ تتم المعالجة يدوياً.\nتواصل: @sookbit",
        "order_confirmed":   "🎉 *تم تأكيد الطلب!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *مفتاحك:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\nشكراً! 🙏 الدعم: @sookbit",
        "order_cancelled":   "❌ تم إلغاء الطلب.",
        "session_expired":   "❌ انتهت الجلسة. ابدأ من جديد.",
        "no_orders":         "📦 ليس لديك أي طلبات بعد.",
        "orders_title":      "📦 *طلباتك:*\n\n",
        "support_msg":       "🛟 تحتاج مساعدة؟ تواصل: @sookbit",
        "back_btn":          "⬅️ رجوع",
        "welcome_back":      "🛒 مرحباً بعودتك، {name}!\n\nاختر خياراً 👇",
        "product_not_found": "❌ المنتج غير موجود.",
    },
    "es": {
        "greeting":          "☀️ ¡Hola, {name}!\n\n🛒 Bienvenido a *{store}*\n\nElige una opción 👇",
        "language_set":      "✅ Idioma establecido en *Español*.",
        "choose_lang":       "🌐 Elige tu idioma:",
        "choose_product":    "🛒 Elige un producto:",
        "no_products":       "❌ No hay productos disponibles.",
        "out_of_stock":      "⚠️ *{name}* está agotado.\nContacta soporte.",
        "pay_instructions":  "{emoji} *{name}*\n💵 Precio: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *Paga con Binance Pay*\n\n🆔 ID de Binance Pay:\n`{binance_id}`\n\n📌 Envía exactamente *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n👇 Pega aquí tu *ID de transacción Binance*:",
        "cancel_btn":        "❌ Cancelar",
        "verifying":         "⏳ Verificando tu pago...\nPor favor espera.",
        "verify_failed":     "❌ *Verificación fallida*\n\nMotivo: {reason}\n\nContacta soporte: @sookbit",
        "no_key":            "✅ *¡Pago verificado!*\n\n⚠️ Procesando manualmente.\nContacta: @sookbit",
        "order_confirmed":   "🎉 *¡Pedido Confirmado!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *Tu Clave:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\n¡Gracias! 🙏 Soporte: @sookbit",
        "order_cancelled":   "❌ Pedido cancelado.",
        "session_expired":   "❌ Sesión expirada. Empieza de nuevo.",
        "no_orders":         "📦 Aún no tienes pedidos.",
        "orders_title":      "📦 *Tus pedidos:*\n\n",
        "support_msg":       "🛟 ¿Necesitas ayuda? Contacta: @sookbit",
        "back_btn":          "⬅️ Volver",
        "welcome_back":      "🛒 ¡Bienvenido de nuevo, {name}!\n\nElige una opción 👇",
        "product_not_found": "❌ Producto no encontrado.",
    },
}


def get_lang(context, user_id: str = None) -> str:
    """Get lang from DB (persistent) with context fallback."""
    if user_id:
        try:
            return get_client_lang(str(user_id))
        except Exception:
            pass
    return context.user_data.get("lang", "en")


def t(context, key: str, user_id: str = None, **kwargs) -> str:
    lang  = get_lang(context, user_id)
    texts = TEXTS.get(lang, TEXTS["en"])
    tpl   = texts.get(key, TEXTS["en"].get(key, key))
    try:
        return tpl.format(**kwargs)
    except Exception:
        return tpl


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_client(user)
    lang     = get_client_lang(str(user.id))
    greeting = t(context, "greeting", user_id=str(user.id),
                 name=user.first_name, store=STORE_NAME)

    await update.effective_message.reply_text(
        greeting, parse_mode="Markdown",
        reply_markup=persistent_menu()
    )
    await update.effective_message.reply_text("👇", reply_markup=main_menu())


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = str(query.from_user.id)

    if data.startswith("setlang_"):
        lang = data.replace("setlang_", "")
        set_client_lang(user_id, lang)
        context.user_data["lang"] = lang
        back_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu", callback_data="back_main")
        ]])
        try:
            await query.message.edit_text(
                t(context, "language_set", user_id=user_id),
                parse_mode="Markdown",
                reply_markup=back_markup
            )
        except Exception:
            await query.message.reply_text(
                t(context, "language_set", user_id=user_id),
                parse_mode="Markdown",
                reply_markup=back_markup
            )
        return

    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar")],
        [InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")],
        [InlineKeyboardButton("⬅️ Back",     callback_data="back_main")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.message.edit_text(
            t(context, "choose_lang", user_id=user_id),
            reply_markup=markup
        )
    except Exception:
        await query.message.reply_text(
            t(context, "choose_lang", user_id=user_id),
            reply_markup=markup
        )
