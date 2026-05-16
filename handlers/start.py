import os
from telegram import Update
from telegram.ext import ContextTypes
from services.clients import create_client
from keyboards.menus import main_menu, persistent_menu

# Translations
TEXTS = {
    "en": {
        "greeting":  "☀️ Hello, {name}!\n\n🛒 Welcome to *{store}*\n\nChoose an option below 👇",
        "language_set": "✅ Language set to *English*.",
        "choose_lang": "🌐 Choose your language:",
    },
    "fr": {
        "greeting":  "☀️ Bonjour, {name} !\n\n🛒 Bienvenue sur *{store}*\n\nChoisissez une option 👇",
        "language_set": "✅ Langue définie sur *Français*.",
        "choose_lang": "🌐 Choisissez votre langue :",
    },
    "ar": {
        "greeting":  "☀️ مرحباً، {name}!\n\n🛒 أهلاً بك في *{store}*\n\nاختر خياراً 👇",
        "language_set": "✅ تم تعيين اللغة إلى *العربية*.",
        "choose_lang": "🌐 اختر لغتك:",
    },
}

STORE_NAME = os.getenv("STORE_NAME", "ProdSeller Store")


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
        reply_markup=persistent_menu()    # bottom persistent keyboard
    )
    await update.effective_message.reply_text(
        "👇",
        reply_markup=main_menu()          # inline buttons
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection inline buttons."""
    query = update.callback_query
    await query.answer()
    data  = query.data  # e.g. "setlang_fr"

    if data.startswith("setlang_"):
        lang = data.replace("setlang_", "")
        context.user_data["lang"] = lang
        await query.message.edit_text(
            t(context, "language_set"),
            parse_mode="Markdown"
        )
        return

    # Show language picker
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English",  callback_data="setlang_en")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="setlang_fr")],
        [InlineKeyboardButton("🇸🇦 العربية",  callback_data="setlang_ar")],
        [InlineKeyboardButton("⬅️ Back",      callback_data="back_main")],
    ]
    await query.message.edit_text(
        t(context, "choose_lang"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
