from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    """Inline menu shown in the welcome message."""
    keyboard = [
        [InlineKeyboardButton("🛍️ Shop",          callback_data="menu_products")],
        [InlineKeyboardButton("📦 Order History",  callback_data="menu_orders")],
        [InlineKeyboardButton("🛟 Support",         callback_data="menu_support")],
        [InlineKeyboardButton("🌐 Language",        callback_data="menu_language")],
    ]
    return InlineKeyboardMarkup(keyboard)


def persistent_menu():
    """
    Persistent Reply Keyboard shown at the bottom of the chat
    (like the HMAI Store screenshot — always visible).
    """
    keyboard = [
        [KeyboardButton("🛍️ Shop"),     KeyboardButton("📦 My Orders")],
        [KeyboardButton("🛟 Support"),   KeyboardButton("🌐 Language")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose an option..."
    )


def products_menu():
    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu():
    keyboard = [
        [InlineKeyboardButton("📋 All Orders",  callback_data="admin_orders")],
        [InlineKeyboardButton("👥 Clients",     callback_data="admin_clients")],
        [InlineKeyboardButton("📊 Stats",       callback_data="admin_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)
