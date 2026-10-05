import logging
from typing import Generator
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Handle SQLite vs PostgreSQL engine arguments
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine_kwargs = {
    "pool_pre_ping": True,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800
    })

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable foreign keys enforcement for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> dict:
    """Verifies that the configured database is reachable and can execute queries."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            scalar = result.scalar()
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            return {
                "connected": scalar == 1,
                "dialect": engine.dialect.name,
                "url": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
                "tables": tables
            }
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return {
            "connected": False,
            "dialect": engine.dialect.name,
            "error": str(exc),
            "tables": []
        }
