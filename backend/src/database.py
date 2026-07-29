"""
Database Configuration Module
-----------------------------
This module establishes the SQLAlchemy connection engine and session factory.
It is configured with aggressive pooling settings to handle high-concurrency 
load testing (e.g., 100+ simultaneous connections) without exhausting the queue.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve database connection string and pool config
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "10"))

if not DATABASE_URL or DATABASE_URL.strip() == "":
    raise ValueError("FATAL: DATABASE_URL environment variable is not set.")

# ==========================================
# ENGINE CONFIGURATION
# ==========================================
# We configure the connection pool to handle the stress test load.
# Formula: Total Capacity = pool_size + max_overflow
# Target: 100 concurrent requests from the script.
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=3600
)

# ==========================================
# SESSION FACTORY
# ==========================================
# autocommit=False: We manually commit transactions to ensure atomicity.
# autoflush=False: We manually flush to control when data is sent to the DB.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models to inherit from
Base = declarative_base()

def get_db():
    """
    Dependency generator for FastAPI path operations.
    Creates a new database session for each request and ensures it is closed 
    regardless of whether the request succeeds or fails.
    
    Yields:
        Session: A SQLAlchemy database session attached to the connection pool.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()