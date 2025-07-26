#!/usr/bin/env python3
"""
Create default admin user for Medical Scribe application
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import get_password_hash
from app.db.base import Base

def create_admin_user():
    """Create default admin user if not exists"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        admin_email = os.getenv("ADMIN_EMAIL", "admin@medical-scribe.com")
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        
        if existing_admin:
            print(f"Admin user {admin_email} already exists")
            return
        
        # Create admin user
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme123!")
        admin_user = User(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"✅ Admin user created successfully!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print("⚠️  Please change the password after first login!")
        
    except Exception as e:
        print(f"ERROR: Failed to create admin user: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()