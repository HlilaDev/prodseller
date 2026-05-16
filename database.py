import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── PostgreSQL on Render (falls back to SQLite for local dev) ─────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")

# Render gives  postgres://...  — SQLAlchemy 1.4+ needs  postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,        # detect dropped connections
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_migrations():
    """Safe incremental migrations — each column added only if missing."""
    with engine.connect() as conn:
        is_sqlite = DATABASE_URL.startswith("sqlite")

        migrations = []

        if is_sqlite:
            migrations = [
                "ALTER TABLE clients ADD COLUMN lang TEXT DEFAULT 'en'",
                "ALTER TABLE orders  ADD COLUMN product_id INTEGER",
                "ALTER TABLE orders  ADD COLUMN delivered_key TEXT",
            ]
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Migration (SQLite): {sql[:60]}")
                except Exception:
                    pass  # column already exists — fine
        else:
            # PostgreSQL: check information_schema before altering
            pg_migrations = [
                ("clients", "lang",          "TEXT DEFAULT 'en'"),
                ("orders",  "product_id",    "INTEGER"),
                ("orders",  "delivered_key", "TEXT"),
            ]
            for table, col, col_def in pg_migrations:
                row = conn.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"
                ), {"t": table, "c": col}).fetchone()
                if not row:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"
                    ))
                    conn.commit()
                    print(f"✅ Migration (PG): ALTER TABLE {table} ADD COLUMN {col}")
                else:
                    print(f"⏭️  Migration skip: {table}.{col} already exists")
