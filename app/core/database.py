# app/core/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Validate environment variable
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

logger = logging.getLogger(__name__)

# Create engine with optimized pool settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,              # Maintain 10 persistent connections
    max_overflow=20,           # Allow 20 additional connections when needed
    pool_pre_ping=True,        # Verify connections before using (fixes your "server closed connection" issue)
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False,                # Set to True for SQL debugging
    connect_args={
        "connect_timeout": 10,  # 10 second timeout
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    }
)

# Add connection pool listeners for logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.info("Database connection established")

@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    logger.info("Database connection closed")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()