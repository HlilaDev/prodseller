from datetime import datetime
from database import SessionLocal
from models import ProductKey, Product


def add_keys(product_id: int, keys: list[str]) -> int:
    """Add a list of keys for a product. Returns count added."""
    db = SessionLocal()
    added = 0
    for k in keys:
        k = k.strip()
        if k:
            db.add(ProductKey(product_id=product_id, key_value=k))
            added += 1
    db.commit()
    db.close()
    return added


def pop_key(product_id: int) -> str | None:
    """Get and mark-used one available key. Returns None if out of stock."""
    db = SessionLocal()
    key = db.query(ProductKey).filter(
        ProductKey.product_id == product_id,
        ProductKey.used == False
    ).first()

    if not key:
        db.close()
        return None

    key.used    = True
    key.used_at = datetime.utcnow()

    # Decrement product stock
    product = db.query(Product).filter(Product.id == product_id).first()
    if product and product.stock > 0:
        product.stock -= 1

    db.commit()
    key_value = key.key_value
    db.close()
    return key_value


def count_available_keys(product_id: int) -> int:
    db = SessionLocal()
    count = db.query(ProductKey).filter(
        ProductKey.product_id == product_id,
        ProductKey.used == False
    ).count()
    db.close()
    return count


def get_all_keys(product_id: int) -> list:
    db = SessionLocal()
    keys = db.query(ProductKey).filter(
        ProductKey.product_id == product_id
    ).order_by(ProductKey.id).all()
    db.close()
    return keys
