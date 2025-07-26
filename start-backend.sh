#!/bin/bash

echo "Starting Medical Scribe Backend on port 8100..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100