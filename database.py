from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

# ✅ Utilise DATABASE_URL (PostgreSQL sur Render) sinon SQLite local
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT  = f"sqlite:///{os.path.join(_BASE_DIR, 'bot.db')}"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT)

# PostgreSQL sur Render utilise parfois "postgres://" → SQLAlchemy veut "postgresql://"
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_migrations():
    """Auto-migrate DB on startup — safe to run multiple times."""
    with engine.connect() as conn:
        migrations = [
            "ALTER TABLE clients ADD COLUMN lang TEXT DEFAULT 'en'",
            "ALTER TABLE orders  ADD COLUMN product_id INTEGER",
            "ALTER TABLE orders  ADD COLUMN delivered_key TEXT",
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✅ Migration: {sql[:50]}")
            except Exception:
                pass
