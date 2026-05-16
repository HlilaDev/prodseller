from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./bot.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
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
