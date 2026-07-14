from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_CONNECT_TIMEOUT_SECONDS, DATABASE_URL


_connect_args = (
    {"connect_timeout": DATABASE_CONNECT_TIMEOUT_SECONDS}
    if DATABASE_URL and DATABASE_URL.startswith("postgresql")
    else {}
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


def is_database_configured() -> bool:
    return SessionLocal is not None


def database_status() -> dict[str, bool]:
    """Report whether PostgreSQL is configured and can accept a connection."""
    if engine is None:
        return {"configured": False, "connected": False}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"configured": True, "connected": True}
    except SQLAlchemyError:
        return {"configured": True, "connected": False}


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    if engine is None:
        return

    from app.db.base import Base
    from app.db import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        # Keep the vector-only application usable if PostgreSQL is offline.
        print(f"PostgreSQL initialization skipped: {exc.__class__.__name__}")
