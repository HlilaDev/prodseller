import asyncio
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from services.products import get_all_products, create_product, toggle_product
from services.orders import get_all_orders, update_order_status, get_order
from services.keys import add_keys, get_all_keys, count_available_keys

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


def is_logged_in(request: Request):
    return request.cookies.get("admin_logged_in") == "yes"


# ── Auth ──────────────────────────────────────────────────────────────────
@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse(request=request, name="dashboard.html")


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/admin/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if (username == os.getenv("ADMIN_WEB_USERNAME")
            and password == os.getenv("ADMIN_WEB_PASSWORD")):
        response = RedirectResponse("/admin", status_code=302)
        response.set_cookie("admin_logged_in", "yes")
        return response
    return templates.TemplateResponse(
        request=request, name="login.html",
        context={"error": "Invalid login"}
    )


# ── Products ──────────────────────────────────────────────────────────────
@router.get("/admin/products", response_class=HTMLResponse)
async def products_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    products = get_all_products() 
    products_with_stock = [
        {"product": p, "keys_available": count_available_keys(p.id)}
        for p in products
    ]
    return templates.TemplateResponse(
        request=request, name="products.html",
        context={"products_with_stock": products_with_stock}
    )


@router.post("/admin/products/add")
async def add_product(request: Request, name: str = Form(...),
                      price: float = Form(...), emoji: str = Form("📦"),
                      stock: int = Form(0)):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    create_product(name, price, emoji, stock)
    return RedirectResponse("/admin/products", status_code=302)


@router.get("/admin/products/toggle/{product_id}")
async def product_toggle(request: Request, product_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    toggle_product(product_id)
    return RedirectResponse("/admin/products", status_code=302)


# ── Keys management ───────────────────────────────────────────────────────
@router.get("/admin/products/{product_id}/keys", response_class=HTMLResponse)
async def keys_page(request: Request, product_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    from services.products import get_all_products
    products = get_all_products()
    product = next((p for p in products if p.id == product_id), None)
    if not product:
        return RedirectResponse("/admin/products", status_code=302)
    keys = get_all_keys(product_id)
    return templates.TemplateResponse(
        request=request, name="keys.html",
        context={"product": product, "keys": keys}
    )


@router.post("/admin/products/{product_id}/keys/add")
async def add_keys_route(request: Request, product_id: int,
                         keys_text: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    key_list = [k.strip() for k in keys_text.splitlines() if k.strip()]
    add_keys(product_id, key_list)
    return RedirectResponse(f"/admin/products/{product_id}/keys", status_code=302)


# ── Orders ────────────────────────────────────────────────────────────────
@router.get("/admin/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    orders = get_all_orders()
    return templates.TemplateResponse(
        request=request, name="orders.html", context={"orders": orders}
    )


def _notify_user_bg(chat_id: str, text: str):
    """Send Telegram message from sync context."""
    from main import telegram_app
    async def _send():
        try:
            await telegram_app.bot.send_message(
                chat_id=chat_id, text=text, parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Notify error: {e}")
    try:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(_send()) if loop.is_running() else loop.run_until_complete(_send())
    except Exception as e:
        print(f"Notify loop error: {e}")


@router.get("/admin/orders/approve/{order_id}")
async def approve_order_web(request: Request, order_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    order = update_order_status(order_id, "approved")
    if order:
        _notify_user_bg(
            order.telegram_id,
            f"🎉 *Order #{order.id} Confirmed!*\n\n"
            f"📦 {order.product_name} — ${order.price} USDT\n\n"
            "Your payment has been verified. Thank you! 🙏"
        )
    return RedirectResponse("/admin/orders", status_code=302)


@router.get("/admin/orders/reject/{order_id}")
async def reject_order_web(request: Request, order_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/admin/login", status_code=302)
    order = update_order_status(order_id, "rejected")
    if order:
        _notify_user_bg(
            order.telegram_id,
            f"❌ *Order #{order.id} Rejected*\n\n"
            f"📦 {order.product_name}\n\n"
            "Payment could not be verified. Contact support: @sookbit"
        )
    return RedirectResponse("/admin/orders", status_code=302)
