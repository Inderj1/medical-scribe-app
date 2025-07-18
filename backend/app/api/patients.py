from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/")
async def get_patients(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of patients"""
    # Implementation placeholder
    return []


@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get patient by ID"""
    # Implementation placeholder
    return {"id": patient_id}