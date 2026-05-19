import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")

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
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_migrations():
    """Safe incremental migrations."""
    with engine.connect() as conn:
        is_sqlite = DATABASE_URL.startswith("sqlite")

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
                    pass
        else:
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
