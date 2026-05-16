import os

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@sookbit")


def get_payment_message(product_name, price, order_id):
    return (
        f"🛒 Product: {product_name}\n"
        f"💵 Price: ${price}\n"
        f"🧾 Order ID: #{order_id}\n\n"
        "✅ Send payment screenshot to admin:\n"
        f"{ADMIN_USERNAME}"
    )


def validate_payment_screenshot(photo):
    """
    Placeholder for future AI/image validation.
    """

    if photo:
        return True

    return False


def generate_crypto_payment(amount):
    """
    Placeholder crypto payment generator.
    """

    return {
        "amount": amount,
        "currency": "USDT",
        "network": "BEP20",
        "address": "0xYourWalletAddress"
    }