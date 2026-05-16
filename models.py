from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from datetime import datetime
from database import Base


class Client(Base):
    __tablename__ = "clients"

    id          = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username    = Column(String, nullable=True)
    first_name  = Column(String, nullable=True)
    lang        = Column(String, default="en")          # ← NEW
    created_at  = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id             = Column(Integer, primary_key=True, index=True)
    telegram_id    = Column(String, index=True)
    product_id     = Column(Integer, nullable=True)
    product_name   = Column(String)
    price          = Column(Float)
    status         = Column(String, default="pending")
    payment_method = Column(String, nullable=True)
    tx_id          = Column(String, nullable=True)
    delivered_key  = Column(String, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String)
    price      = Column(Float)
    emoji      = Column(String, default="📦")
    stock      = Column(Integer, default=0)
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductKey(Base):
    __tablename__ = "product_keys"

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    key_value  = Column(String, nullable=False)
    used       = Column(Boolean, default=False)
    used_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
