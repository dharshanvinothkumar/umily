"""
Umily — Database Engine & Session Management

SQLAlchemy async engine connected to SQLite.
Provides session factory and base model class.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings, BASE_DIR


# Ensure data directory exists
data_dir = BASE_DIR / "data"
data_dir.mkdir(exist_ok=True)

# SQLite database path
db_path = data_dir / "umily.db"
DATABASE_URL = f"sqlite:///{db_path}"

# Create synchronous engine (SQLite doesn't benefit much from async in practice)
engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_db():
    """Dependency: yields a database session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables. Called on application startup."""
    from app.database import models as _models  # noqa: F401 — ensure models are registered

    Base.metadata.create_all(bind=engine)
