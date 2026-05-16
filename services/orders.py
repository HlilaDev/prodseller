from database import SessionLocal
from models import Order


def create_order(telegram_id, product_id, product_name, price,
                 payment_method=None, tx_id=None):
    db = SessionLocal()
    order = Order(
        telegram_id    = str(telegram_id),
        product_id     = product_id,
        product_name   = product_name,
        price          = price,
        status         = "pending",
        payment_method = payment_method,
        tx_id          = tx_id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    db.close()
    return order


def update_order(order_id, **kwargs):
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        for k, v in kwargs.items():
            setattr(order, k, v)
        db.commit()
        db.refresh(order)
    db.close()
    return order


def update_order_status(order_id, status):
    return update_order(order_id, status=status)


def get_order(order_id):
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    db.close()
    return order


def get_user_orders(telegram_id):
    db = SessionLocal()
    orders = db.query(Order).filter(
        Order.telegram_id == str(telegram_id)
    ).order_by(Order.created_at.desc()).all()
    db.close()
    return orders


def get_all_orders():
    db = SessionLocal()
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    db.close()
    return orders
