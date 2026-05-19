from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from datetime import datetime
from database import Base


class Client(Base):
    __tablename__ = "clients"

    id          = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username    = Column(String, nullable=True)
    first_name  = Column(String, nullable=True)
    lang        = Column(String, default="en")
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


class PendingPayment(Base):
    """
    Tracks a Binance Pay payment awaiting note-based auto-detection.
    note  = unique 8-char code shown to user in the Remark field
    expires_at = 30 minutes from creation
    """
    __tablename__ = "pending_payments"

    id          = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, index=True)
    product_id  = Column(Integer, nullable=False)
    price       = Column(Float,  nullable=False)
    note        = Column(String, unique=True, index=True)  # e.g. T00LS-9BE380
    message_id  = Column(Integer, nullable=True)           # Telegram message to edit
    chat_id     = Column(String,  nullable=True)
    expires_at  = Column(DateTime, nullable=False)
    fulfilled   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
