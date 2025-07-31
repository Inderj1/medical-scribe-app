#!/usr/bin/env python
"""Run database migrations with retry logic for PostgreSQL startup."""
import sys
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from app.db.session import engine
from app.db.base_class import Base

MAX_RETRIES = 10
RETRY_DELAY = 2  # seconds

def run_migrations():
    """Run database migrations with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Attempting to connect to database (attempt {attempt + 1}/{MAX_RETRIES})...")
            
            # Test connection first
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # If connection successful, run migrations
            print("Database connection successful, running migrations...")
            Base.metadata.create_all(bind=engine)
            print("Database migrations completed successfully!")
            return True
            
        except OperationalError as e:
            if "database system is starting up" in str(e) or "could not connect" in str(e):
                if attempt < MAX_RETRIES - 1:
                    print(f"Database not ready yet, waiting {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Failed to connect to database after {MAX_RETRIES} attempts")
                    raise
            else:
                # Different error, don't retry
                raise
    
    return False

if __name__ == "__main__":
    try:
        success = run_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)