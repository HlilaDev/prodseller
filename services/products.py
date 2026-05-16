from database import SessionLocal
from models import Product


def get_all_products():
    db = SessionLocal()
    products = db.query(Product).order_by(Product.id.desc()).all()
    db.close()
    return products


def get_active_products():
    db = SessionLocal()
    products = db.query(Product).filter(Product.active == True).all()
    db.close()
    return products


def create_product(name, price, emoji, stock):
    db = SessionLocal()

    product = Product(
        name=name,
        price=price,
        emoji=emoji,
        stock=stock,
        active=True
    )

    db.add(product)
    db.commit()
    db.refresh(product)
    db.close()

    return product


def toggle_product(product_id):
    db = SessionLocal()

    product = db.query(Product).filter(Product.id == product_id).first()

    if product:
        product.active = not product.active
        db.commit()

    db.close()
    return product