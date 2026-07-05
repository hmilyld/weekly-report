"""Add encryption fields to DailyReport, WeeklyReport, Task, and User tables."""

import sqlite3
import sys
from pathlib import Path


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns for each table
    def existing_columns(table: str) -> set[str]:
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    # Columns to add to report/task tables
    encryption_columns = [
        ("content_encrypted", "TEXT"),
        ("content_salt", "VARCHAR(64)"),
        ("content_nonce", "VARCHAR(64)"),
        ("content_tag", "VARCHAR(64)"),
        ("content_version", "INTEGER"),
    ]

    for table in ("daily_reports", "weekly_reports", "tasks"):
        cols = existing_columns(table)
        for name, col_type in encryption_columns:
            if name not in cols:
                print(f"  Adding {table}.{name}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")
            else:
                print(f"  {table}.{name} already exists, skipping")

    # Add needs_encryption_migration to users
    user_cols = existing_columns("users")
    if "needs_encryption_migration" not in user_cols:
        print("  Adding users.needs_encryption_migration")
        cursor.execute("ALTER TABLE users ADD COLUMN needs_encryption_migration BOOLEAN DEFAULT 1")
    else:
        print("  users.needs_encryption_migration already exists, skipping")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    # Default path: backend/data/weekly_report.db
    default_db = Path(__file__).parent / "data" / "weekly_report.db"
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(default_db)
    print(f"Migrating database: {db_path}")
    migrate(db_path)
