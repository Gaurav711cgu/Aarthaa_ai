from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Primary PostgreSQL URL
if settings.DATABASE_URL:
    PG_URL = settings.DATABASE_URL
    if PG_URL.startswith("postgres://"):
        PG_URL = PG_URL.replace("postgres://", "postgresql://", 1)
else:
    PG_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# Fallback SQLite URL
SQLITE_URL = "sqlite:///artha_local.db"

engine = None
is_postgres_active = False

try:
    # Try creating PostgreSQL engine
    logger.info("Attempting connection to PostgreSQL...")
    engine = create_engine(
        PG_URL,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
        pool_pre_ping=True
    )
    # Test connection immediately
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    is_postgres_active = True
    logger.info("PostgreSQL connection established successfully.")
except (OperationalError, Exception) as e:
    # Sanitize connection error string to prevent credentials leakage in logs
    safe_error = str(e).split("\n")[0][:200]
    if settings.POSTGRES_PASSWORD and settings.POSTGRES_PASSWORD in safe_error:
        safe_error = safe_error.replace(settings.POSTGRES_PASSWORD, "***")
    logger.warning(
        f"PostgreSQL connection failed ({safe_error}). Falling back to SQLite local database: {SQLITE_URL}"
    )
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False} if SQLITE_URL.startswith("sqlite") else {}
    )
    is_postgres_active = False

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI db session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
