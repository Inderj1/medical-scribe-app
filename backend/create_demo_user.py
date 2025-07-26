#!/usr/bin/env python3
"""Create a demo user for testing the application"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models.user import User
from app.core.auth import get_password_hash

def create_demo_user():
    """Create a demo user if it doesn't exist"""
    db: Session = SessionLocal()
    
    try:
        # Check if demo user already exists
        demo_user = db.query(User).filter(User.username == "demo").first()
        
        if demo_user:
            print("Demo user already exists!")
            return
        
        # Create demo user
        demo_user = User(
            username="demo",
            email="demo@example.com",
            full_name="Demo User",
            hashed_password=get_password_hash("demo123"),
            role="physician",
            is_active=True
        )
        
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        
        print(f"Demo user created successfully!")
        print(f"Username: demo")
        print(f"Password: demo123")
        print(f"User ID: {demo_user.id}")
        
    except Exception as e:
        print(f"Error creating demo user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_user()