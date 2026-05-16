from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import SessionLocal
from models import Client


def save_client(user):
    db = SessionLocal()

    client = db.query(Client).filter(
        Client.telegram_id == str(user.id)
    ).first()

    if not client:
        client = Client(
            telegram_id=str(user.id),
            username=user.username,
            first_name=user.first_name
        )

        db.add(client)
        db.commit()

    db.close()


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Products", callback_data="buy")],
        [InlineKeyboardButton("📦 My Orders", callback_data="orders")],
        [InlineKeyboardButton("🛟 Support", callback_data="support")]
    ]

    return InlineKeyboardMarkup(keyboard)


def product_menu():
    keyboard = [
        [InlineKeyboardButton("🤖 ChatGPT Plus | $3", callback_data="chatgpt")],
        [InlineKeyboardButton("🎬 CapCut Pro | $1", callback_data="capcut")],
        [InlineKeyboardButton("💎 Gemini Pro | $1", callback_data="gemini")]
    ]

    return InlineKeyboardMarkup(keyboard)


def format_order(order):
    return (
        f"🧾 Order #{order.id}\n"
        f"📦 Product: {order.product_name}\n"
        f"💵 Price: ${order.price}\n"
        f"📌 Status: {order.status}"
    )