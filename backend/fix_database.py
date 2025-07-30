#!/usr/bin/env python3
"""Fix missing database columns"""
import psycopg2
from psycopg2 import sql
import os
from urllib.parse import urlparse

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/medical_scribe_db")

# Parse URL
result = urlparse(DATABASE_URL)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

# Connect to database
conn = psycopg2.connect(
    database=database,
    user=username,
    password=password,
    host=hostname,
    port=port
)

cur = conn.cursor()

# Add missing columns to patients table
try:
    cur.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS insurance_info JSONB")
    print("Added insurance_info column to patients table")
except Exception as e:
    print(f"Error adding insurance_info: {e}")

try:
    cur.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS emergency_contact JSONB")
    print("Added emergency_contact column to patients table")
except Exception as e:
    print(f"Error adding emergency_contact: {e}")

# Add missing columns to encounters table
try:
    cur.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS ehr_encounter_id VARCHAR")
    print("Added ehr_encounter_id column to encounters table")
except Exception as e:
    print(f"Error adding ehr_encounter_id: {e}")

try:
    cur.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS user_id UUID")
    print("Added user_id column to encounters table")
except Exception as e:
    print(f"Error adding user_id: {e}")

try:
    cur.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS provider_name VARCHAR")
    print("Added provider_name column to encounters table")
except Exception as e:
    print(f"Error adding provider_name: {e}")

try:
    cur.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS location VARCHAR")
    print("Added location column to encounters table")
except Exception as e:
    print(f"Error adding location: {e}")

try:
    cur.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS extra_metadata JSONB DEFAULT '{}'::jsonb")
    print("Added extra_metadata column to encounters table")
except Exception as e:
    print(f"Error adding extra_metadata: {e}")

# Add missing columns to transcriptions table
try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS audio_file_path VARCHAR")
    print("Added audio_file_path column to transcriptions table")
except Exception as e:
    print(f"Error adding audio_file_path: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS audio_duration_seconds FLOAT")
    print("Added audio_duration_seconds column to transcriptions table")
except Exception as e:
    print(f"Error adding audio_duration_seconds: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT")
    print("Added file_size_bytes column to transcriptions table")
except Exception as e:
    print(f"Error adding file_size_bytes: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS partial_transcript TEXT")
    print("Added partial_transcript column to transcriptions table")
except Exception as e:
    print(f"Error adding partial_transcript: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS error_message TEXT")
    print("Added error_message column to transcriptions table")
except Exception as e:
    print(f"Error adding error_message: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP")
    print("Added completed_at column to transcriptions table")
except Exception as e:
    print(f"Error adding completed_at: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS transcript TEXT")
    print("Added transcript column to transcriptions table")
except Exception as e:
    print(f"Error adding transcript: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS status VARCHAR")
    print("Added status column to transcriptions table")
except Exception as e:
    print(f"Error adding status: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0")
    print("Added progress column to transcriptions table")
except Exception as e:
    print(f"Error adding progress: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Added created_at column to transcriptions table")
except Exception as e:
    print(f"Error adding created_at: {e}")

try:
    cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Added updated_at column to transcriptions table")
except Exception as e:
    print(f"Error adding updated_at: {e}")

# Commit changes
conn.commit()
print("Database schema updated successfully")

# Close connection
cur.close()
conn.close()