#!/usr/bin/env python3
"""Check database schema for encounters table"""

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Check if patient_id is nullable
    result = conn.execute(text("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = 'encounters'
        AND column_name = 'patient_id';
    """))
    
    for row in result:
        print(f"Column: {row[0]}")
        print(f"Nullable: {row[1]}")
        print(f"Data type: {row[2]}")