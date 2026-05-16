import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.clients import create_client
from keyboards.menus import main_menu, persistent_menu

STORE_NAME = os.getenv("STORE_NAME", "ProdSeller Store")

# ── Full translation table ────────────────────────────────────────────────
TEXTS = {
    "en": {
        "greeting":          "☀️ Hello, {name}!\n\n🛒 Welcome to *{store}*\n\nChoose an option below 👇",
        "language_set":      "✅ Language set to *English*.",
        "choose_lang":       "🌐 Choose your language:",
        "choose_product":    "🛒 Choose a product:",
        "no_products":       "❌ No products available right now.",
        "out_of_stock":      "⚠️ *{name}* is currently out of stock.\nPlease try again later or contact support.",
        "pay_instructions":  "{emoji} *{name}*\n💵 Price: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *Pay via Binance Pay*\n\n🆔 Binance Pay ID:\n`{binance_id}`\n\n📌 Send exactly *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n👇 After payment, paste your *Binance Transaction ID* here:",
        "cancel_btn":        "❌ Cancel",
        "verifying":         "⏳ Verifying your payment with Binance...\nPlease wait.",
        "verify_failed":     "❌ *Payment verification failed*\n\nReason: {reason}\n\nPlease check your Transaction ID and try again, or contact support: @sookbit",
        "no_key":            "✅ *Payment verified!*\n\n⚠️ We're processing your order manually.\nYour key will be sent shortly. Contact: @sookbit",
        "order_confirmed":   "🎉 *Payment Verified & Order Confirmed!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *Your Key/Code:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\nThank you for your purchase! 🙏\nFor support: @sookbit",
        "order_cancelled":   "❌ Order cancelled.",
        "session_expired":   "❌ Session expired. Please start again.",
        "no_orders":         "📦 You have no orders yet.",
        "orders_title":      "📦 *Your orders:*\n\n",
        "support_msg":       "🛟 Need help? Contact: @sookbit",
        "back_btn":          "⬅️ Back",
        "welcome_back":      "🛒 Welcome back, {name}!\n\nChoose an option below 👇",
        "product_not_found": "❌ Product not found.",
    },
    "ar": {
        "greeting":          "☀️ مرحباً، {name}!\n\n🛒 أهلاً بك في *{store}*\n\nاختر خياراً 👇",
        "language_set":      "✅ تم تعيين اللغة إلى *العربية*.",
        "choose_lang":       "🌐 اختر لغتك:",
        "choose_product":    "🛒 اختر منتجاً:",
        "no_products":       "❌ لا توجد منتجات متاحة حالياً.",
        "out_of_stock":      "⚠️ *{name}* غير متوفر حالياً.\nحاول مرة أخرى لاحقاً أو تواصل مع الدعم.",
        "pay_instructions":  "{emoji} *{name}*\n💵 السعر: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *الدفع عبر Binance Pay*\n\n🆔 معرّف Binance Pay:\n`{binance_id}`\n\n📌 أرسل *${price} USDT* بالضبط\n\n━━━━━━━━━━━━━━━━━━\n👇 بعد الدفع، أرسل *رقم معاملة Binance* هنا:",
        "cancel_btn":        "❌ إلغاء",
        "verifying":         "⏳ جارٍ التحقق من دفعتك عبر Binance...\nيرجى الانتظار.",
        "verify_failed":     "❌ *فشل التحقق من الدفع*\n\nالسبب: {reason}\n\nتحقق من رقم المعاملة وحاول مجدداً، أو تواصل مع الدعم: @sookbit",
        "no_key":            "✅ *تم التحقق من الدفع!*\n\n⚠️ سيتم معالجة طلبك يدوياً.\nسيتم إرسال مفتاحك قريباً. تواصل: @sookbit",
        "order_confirmed":   "🎉 *تم التحقق من الدفع وتأكيد الطلب!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *مفتاحك/كودك:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\nشكراً لشرائك! 🙏\nللدعم: @sookbit",
        "order_cancelled":   "❌ تم إلغاء الطلب.",
        "session_expired":   "❌ انتهت الجلسة. يرجى البدء من جديد.",
        "no_orders":         "📦 ليس لديك أي طلبات بعد.",
        "orders_title":      "📦 *طلباتك:*\n\n",
        "support_msg":       "🛟 تحتاج مساعدة؟ تواصل مع: @sookbit",
        "back_btn":          "⬅️ رجوع",
        "welcome_back":      "🛒 مرحباً بعودتك، {name}!\n\nاختر خياراً 👇",
        "product_not_found": "❌ المنتج غير موجود.",
    },
    "es": {
        "greeting":          "☀️ ¡Hola, {name}!\n\n🛒 Bienvenido a *{store}*\n\nElige una opción 👇",
        "language_set":      "✅ Idioma establecido en *Español*.",
        "choose_lang":       "🌐 Elige tu idioma:",
        "choose_product":    "🛒 Elige un producto:",
        "no_products":       "❌ No hay productos disponibles ahora mismo.",
        "out_of_stock":      "⚠️ *{name}* está agotado.\nIntenta más tarde o contacta soporte.",
        "pay_instructions":  "{emoji} *{name}*\n💵 Precio: *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n💳 *Paga con Binance Pay*\n\n🆔 ID de Binance Pay:\n`{binance_id}`\n\n📌 Envía exactamente *${price} USDT*\n\n━━━━━━━━━━━━━━━━━━\n👇 Después de pagar, pega aquí tu *ID de transacción de Binance*:",
        "cancel_btn":        "❌ Cancelar",
        "verifying":         "⏳ Verificando tu pago en Binance...\nPor favor espera.",
        "verify_failed":     "❌ *Verificación de pago fallida*\n\nMotivo: {reason}\n\nRevisa tu ID de transacción e inténtalo de nuevo, o contacta soporte: @sookbit",
        "no_key":            "✅ *¡Pago verificado!*\n\n⚠️ Tu pedido se está procesando manualmente.\nTu clave será enviada pronto. Contacta: @sookbit",
        "order_confirmed":   "🎉 *¡Pago Verificado y Pedido Confirmado!*\n\n📦 {emoji} *{name}*\n💵 ${price} USDT\n\n━━━━━━━━━━━━━━━━━━\n🔑 *Tu Clave/Código:*\n`{key}`\n━━━━━━━━━━━━━━━━━━\n\n¡Gracias por tu compra! 🙏\nSoporte: @sookbit",
        "order_cancelled":   "❌ Pedido cancelado.",
        "session_expired":   "❌ Sesión expirada. Por favor empieza de nuevo.",
        "no_orders":         "📦 Aún no tienes pedidos.",
        "orders_title":      "📦 *Tus pedidos:*\n\n",
        "support_msg":       "🛟 ¿Necesitas ayuda? Contacta: @sookbit",
        "back_btn":          "⬅️ Volver",
        "welcome_back":      "🛒 ¡Bienvenido de nuevo, {name}!\n\nElige una opción 👇",
        "product_not_found": "❌ Producto no encontrado.",
    },
}


def get_lang(context) -> str:
    return context.user_data.get("lang", "en")


def t(context, key: str, **kwargs) -> str:
    lang  = get_lang(context)
    texts = TEXTS.get(lang, TEXTS["en"])
    return texts.get(key, TEXTS["en"].get(key, key)).format(**kwargs)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_client(user)

    greeting = t(context, "greeting", name=user.first_name, store=STORE_NAME)

    await update.effective_message.reply_text(
        greeting,
        parse_mode="Markdown",
        reply_markup=persistent_menu()
    )
    await update.effective_message.reply_text(
        "👇",
        reply_markup=main_menu()
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("setlang_"):
        lang = data.replace("setlang_", "")
        context.user_data["lang"] = lang
        await query.message.edit_text(
            t(context, "language_set"),
            parse_mode="Markdown"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar")],
        [InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")],
        [InlineKeyboardButton("⬅️ Back",     callback_data="back_main")],
    ]
    await query.message.edit_text(
        t(context, "choose_lang"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
