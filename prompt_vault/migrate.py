"""Simple migration for adding new columns to existing SQLite database.
Safe to run multiple times — only adds columns that don't exist yet.
"""
import sqlite3
import logging

from prompt_vault.config import BASE_DIR

logger = logging.getLogger("prompt_vault.migrate")

DB_PATH = BASE_DIR / "prompt_vault.db"

MIGRATIONS = [
    ("prompt_logs", "status", "TEXT DEFAULT 'success'"),
    ("prompt_logs", "error_message", "TEXT"),
    ("prompt_logs", "prompt_tokens", "INTEGER"),
    ("prompt_logs", "completion_tokens", "INTEGER"),
    ("prompt_logs", "total_tokens", "INTEGER"),
    ("prompt_logs", "replay_of", "INTEGER"),
]


def run_migrations():
    if not DB_PATH.exists():
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    for table, column, col_type in MIGRATIONS:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            logger.info("Added column %s.%s", table, column)
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.commit()
    conn.close()
