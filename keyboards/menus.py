from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 Buy Products",
                callback_data="menu_products"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 My Orders",
                callback_data="menu_orders"
            )
        ],
        [
            InlineKeyboardButton(
                "🛟 Support",
                callback_data="menu_support"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def products_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🤖 ChatGPT Plus 30 Days | $3",
                callback_data="buy_chatgpt"
            )
        ],
        [
            InlineKeyboardButton(
                "🎬 CapCut Pro 30 Days | $1",
                callback_data="buy_capcut"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Gemini Pro 1 Month | $1",
                callback_data="buy_gemini"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back_main"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def admin_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "📋 All Orders",
                callback_data="admin_orders"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Clients",
                callback_data="admin_clients"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Stats",
                callback_data="admin_stats"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)