"""Additive schema migration on a legacy SQLite database.

The fixtures point app.schema_migrations at a temporary database so the
developer's real ./data/weekly_report.db is never opened.
"""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import app.schema_migrations as migrations
from app.models import AppConfig, Base

LEGACY_USERS = (
    "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50), password_hash VARCHAR(255))"
)
LEGACY_DAILY = (
    "CREATE TABLE daily_reports ("
    "id INTEGER PRIMARY KEY, user_id INTEGER, date VARCHAR(10), content TEXT)"
)


@pytest.fixture()
def legacy_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text(LEGACY_USERS))
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash) "
                "VALUES (1, 'admin', 'x'), (2, 'bob', 'y')"
            )
        )
        connection.execute(text(LEGACY_DAILY))
        connection.execute(
            text(
                "INSERT INTO daily_reports (id, user_id, date, content) "
                "VALUES (1, 1, '2026-11-01', '旧内容')"
            )
        )
    # init_database() creates missing tables first, which leaves existing legacy
    # tables untouched; migrate_schema() then adds what those tables lack.
    Base.metadata.create_all(engine)
    monkeypatch.setattr(migrations, "engine", engine)
    monkeypatch.setattr(migrations, "SessionLocal", sessionmaker(bind=engine))
    return engine


def columns(engine, table):
    return {column["name"] for column in inspect(engine).get_columns(table)}


def test_adds_every_user_column(legacy_engine):
    migrations.migrate_schema()

    expected = {name for name, _definition in migrations.USER_COLUMN_MIGRATIONS}
    assert expected <= columns(legacy_engine, "users")


def test_first_user_becomes_admin_only_once(legacy_engine):
    migrations.migrate_schema()

    with legacy_engine.begin() as connection:
        roles = dict(connection.execute(text("SELECT id, role FROM users")).all())
    assert roles == {1: "admin", 2: "user"}


def test_adds_content_columns_and_keeps_existing_rows(legacy_engine):
    migrations.migrate_schema()

    expected = {name for name, _definition in migrations.CONTENT_COLUMN_MIGRATIONS}
    assert expected <= columns(legacy_engine, "daily_reports")
    with legacy_engine.begin() as connection:
        assert connection.execute(text("SELECT content FROM daily_reports")).scalar() == "旧内容"


def test_migration_is_idempotent(legacy_engine):
    migrations.migrate_schema()
    before = columns(legacy_engine, "users")

    migrations.migrate_schema()

    assert columns(legacy_engine, "users") == before
    with legacy_engine.begin() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar() == 2


def test_empty_database_is_left_alone(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    monkeypatch.setattr(migrations, "engine", engine)

    migrations.migrate_schema()

    assert inspect(engine).get_table_names() == []
    assert migrations._existing_tables() == set()


def test_seed_app_config_creates_one_row(legacy_engine):
    migrations._seed_app_config()
    migrations._seed_app_config()

    with migrations.SessionLocal() as db:
        rows = db.query(AppConfig).all()
    assert len(rows) == 1
    assert rows[0].id == 1
    assert rows[0].llm_model_name
