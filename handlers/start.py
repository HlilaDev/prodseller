from telegram import Update
from telegram.ext import ContextTypes
from services.clients import create_client
from keyboards.menus import main_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    create_client(user)

    await update.message.reply_text(
        f"🛒 Welcome to ProdSeller Store, {user.first_name}!\n\n"
        "Choose an option below 👇",
        reply_markup=main_menu()
    )
