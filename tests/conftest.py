"""
Umily — Pytest Configuration and Fixtures
Shared in-memory SQLite database setup for all tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.database.database import Base, get_db
from app.database import models as _models  # noqa: F401
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test function, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """TestClient instance for FastAPI endpoints."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provides a clean database session for unit tests."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
