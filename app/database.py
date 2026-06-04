from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings
from app.logger import logger

# Create engine
engine = create_engine(
    settings.database_url,
    # connection pool adjustments for production
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# DB dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error occurred", extra={"error": str(e)})
        raise
    finally:
        db.close()
