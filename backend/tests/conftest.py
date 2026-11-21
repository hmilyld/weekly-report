"""Shared test setup: a fixed master key so tests never touch dev key files."""

import base64
import os

import pytest

# Must be set before any app module imports app.config.
os.environ.setdefault("ENCRYPTION_MASTER_KEY", base64.b64encode(bytes(range(32))).decode())


@pytest.fixture()
def api_env():
    """TestClient + in-memory DB shared across threads (endpoints only, no lifespan)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import main
    from app.database import get_db
    from app.key_cache import key_cache
    from app.models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    def override_get_db():
        # Mirror app.database.get_db: rollback on error, commit on success.
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()

    main.app.dependency_overrides[get_db] = override_get_db
    client = TestClient(main.app)
    yield client, session
    main.app.dependency_overrides.clear()
    session.close()
    key_cache.clear()
