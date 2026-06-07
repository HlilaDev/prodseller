"""
admin/api.py — JSON REST API for the React dashboard
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import os

from services.products import (
    get_all_products, create_product, toggle_product, delete_product
)
from services.orders import get_all_orders, update_order_status
from services.keys import add_keys, get_all_keys, count_available_keys, delete_all_keys
from models import Order, Product, Client
from database import SessionLocal

api_router = APIRouter(prefix="/api", tags=["admin-api"])


def require_auth(request: Request):
    if request.cookies.get("admin_logged_in") != "yes":
        raise HTTPException(status_code=401, detail="Unauthorized")


class ProductCreate(BaseModel):
    name: str
    price: float
    emoji: str = "📦"
    stock: int = 0


class KeysAdd(BaseModel):
    keys: List[str]


class OrderAction(BaseModel):
    action: str  # "approve" | "reject"


# ── Stats ──────────────────────────────────────────────────────────────────

@api_router.get("/stats")
def get_stats(request: Request, _=Depends(require_auth)):
    db = SessionLocal()
    try:
        orders = db.query(Order).all()
        total_orders    = len(orders)
        pending_orders  = sum(1 for o in orders if o.status == "pending")
        approved_orders = sum(1 for o in orders if o.status == "approved")
        total_revenue   = sum(o.price for o in orders if o.status == "approved")

        products        = db.query(Product).all()
        total_products  = len(products)
        active_products = sum(1 for p in products if p.active)

        clients       = db.query(Client).all()
        total_clients = len(clients)

        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        revenue_by_day = {}
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            revenue_by_day[day.strftime("%a")] = 0

        for o in orders:
            if o.status == "approved" and o.created_at:
                label = o.created_at.date().strftime("%a")
                if label in revenue_by_day:
                    revenue_by_day[label] += o.price

        return {
            "total_orders":    total_orders,
            "pending_orders":  pending_orders,
            "approved_orders": approved_orders,
            "total_revenue":   round(total_revenue, 2),
            "total_products":  total_products,
            "active_products": active_products,
            "total_clients":   total_clients,
            "revenue_chart":   [{"day": d, "revenue": round(v, 2)} for d, v in revenue_by_day.items()],
        }
    finally:
        db.close()


# ── Products ───────────────────────────────────────────────────────────────

@api_router.get("/products")
def list_products(request: Request, _=Depends(require_auth)):
    products = get_all_products()
    return [
        {
            "id":             p.id,
            "name":           p.name,
            "price":          p.price,
            "emoji":          p.emoji,
            "stock":          p.stock,
            "active":         p.active,
            "keys_available": count_available_keys(p.id),
            "created_at":     p.created_at.isoformat() if p.created_at else None,
        }
        for p in products
    ]


@api_router.post("/products")
def add_product(data: ProductCreate, request: Request, _=Depends(require_auth)):
    p = create_product(data.name, data.price, data.emoji, data.stock)
    return {"id": p.id, "name": p.name, "price": p.price, "emoji": p.emoji,
            "stock": p.stock, "active": p.active, "keys_available": 0}


@api_router.patch("/products/{product_id}/toggle")
def toggle(product_id: int, request: Request, _=Depends(require_auth)):
    p = toggle_product(product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return {"id": p.id, "active": p.active}


@api_router.delete("/products/{product_id}")
def remove_product(product_id: int, request: Request, _=Depends(require_auth)):
    delete_product(product_id)
    return {"ok": True}


# ── Keys ───────────────────────────────────────────────────────────────────

@api_router.get("/products/{product_id}/keys")
def list_keys(product_id: int, request: Request, _=Depends(require_auth)):
    keys = get_all_keys(product_id)
    return [
        {
            "id":        k.id,
            "key_value": k.key_value,
            "used":      k.used,
            "used_at":   k.used_at.isoformat() if k.used_at else None,
        }
        for k in keys
    ]


@api_router.post("/products/{product_id}/keys")
def bulk_add_keys(product_id: int, data: KeysAdd, request: Request, _=Depends(require_auth)):
    added = add_keys(product_id, data.keys)
    return {"added": added}


@api_router.delete("/products/{product_id}/keys")
def remove_all_keys(product_id: int, request: Request, _=Depends(require_auth)):
    deleted = delete_all_keys(product_id)
    return {"deleted": deleted}


# ── Orders ─────────────────────────────────────────────────────────────────

@api_router.get("/orders")
def list_orders(request: Request, _=Depends(require_auth)):
    orders = get_all_orders()
    return [
        {
            "id":             o.id,
            "telegram_id":    o.telegram_id,
            "product_name":   o.product_name,
            "price":          o.price,
            "status":         o.status,
            "payment_method": o.payment_method,
            "tx_id":          o.tx_id,
            "delivered_key":  o.delivered_key,
            "created_at":     o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@api_router.patch("/orders/{order_id}")
def update_order(order_id: int, data: OrderAction, request: Request, _=Depends(require_auth)):
    if data.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")
    status = "approved" if data.action == "approve" else "rejected"
    order  = update_order_status(order_id, status)
    if not order:
        raise HTTPException(404, "Order not found")

    import asyncio
    from main import telegram_app
    msg = (
        f"🎉 *Order #{order.id} Confirmed!*\n\n📦 {order.product_name} — ${order.price} USDT\n\nThank you! 🙏"
        if data.action == "approve" else
        f"❌ *Order #{order.id} Rejected*\n\n📦 {order.product_name}\n\nContact support."
    )
    async def _notify():
        try:
            await telegram_app.bot.send_message(chat_id=order.telegram_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Notify error: {e}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_notify())
        else:
            loop.run_until_complete(_notify())
    except Exception as e:
        print(f"Notify loop error: {e}")

    return {"id": order.id, "status": order.status}


# ── Clients ────────────────────────────────────────────────────────────────

@api_router.get("/clients")
def list_clients(request: Request, _=Depends(require_auth)):
    db = SessionLocal()
    try:
        clients = db.query(Client).order_by(Client.created_at.desc()).all()
        return [
            {
                "id":          c.id,
                "telegram_id": c.telegram_id,
                "username":    c.username,
                "first_name":  c.first_name,
                "lang":        c.lang,
                "created_at":  c.created_at.isoformat() if c.created_at else None,
            }
            for c in clients
        ]
    finally:
        db.close()
