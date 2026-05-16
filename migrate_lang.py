"""Run once to add 'lang' column to existing clients table."""
import sqlite3, os

db_path = os.getenv("DB_PATH", "bot.db")
try:
    conn = sqlite3.connect(db_path)
    conn.execute("ALTER TABLE clients ADD COLUMN lang TEXT DEFAULT 'en'")
    conn.commit()
    conn.close()
    print("✅ Migration done — lang column added.")
except sqlite3.OperationalError as e:
    print(f"ℹ️  {e}")  # column already exists
