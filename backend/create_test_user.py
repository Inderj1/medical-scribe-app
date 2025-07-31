#!/usr/bin/env python3
"""Create a test user for development"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from datetime import datetime


def create_test_user():
    """Create a test user"""
    db: Session = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        
        if existing_user:
            print("Test user already exists")
            # Update password to ensure it's correct
            existing_user.hashed_password = get_password_hash("test123")
            db.commit()
            print("Password updated for test user")
        else:
            # Create new user
            user = User(
                email="test@example.com",
                full_name="Test User",
                hashed_password=get_password_hash("test123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            print("Test user created successfully")
            
        print("\nTest user credentials:")
        print("Email: test@example.com")
        print("Password: test123")
        
    except Exception as e:
        print(f"Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()