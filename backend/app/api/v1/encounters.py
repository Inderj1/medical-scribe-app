"""Encounters API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.services.ehrbase.client import EHRBaseClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/")
async def create_encounter(
    encounter_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new encounter"""
    
    # Validate patient exists
    patient_id = encounter_data.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")
    
    patient = None
    # Try to find patient by UUID first
    try:
        patient_uuid = uuid.UUID(patient_id)
        patient = db.query(Patient).filter(Patient.id == patient_uuid).first()
    except ValueError:
        # Not a UUID, try as EHR ID
        patient = db.query(Patient).filter(Patient.ehr_id == patient_id).first()
    
    if not patient:
        # If patient is provided by EHR ID and doesn't exist locally, return error
        raise HTTPException(
            status_code=404, 
            detail="Patient not found. Please ensure patient is synced from EHRBase first."
        )
    
    # Create encounter
    encounter = Encounter(
        patient_id=patient.id,
        user_id=current_user.id,
        chief_complaint=encounter_data.get("chief_complaint"),
        encounter_type=encounter_data.get("encounter_type", "office_visit"),
        provider_name=encounter_data.get("provider_name", current_user.full_name),
        location=encounter_data.get("location"),
        extra_metadata=encounter_data.get("metadata", {})
    )
    
    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    
    return {
        "id": str(encounter.id),
        "patient_id": str(encounter.patient_id),
        "chief_complaint": encounter.chief_complaint,
        "encounter_date": encounter.encounter_date.isoformat(),
        "status": encounter.status,
        "created": True
    }


@router.get("/{encounter_id}")
async def get_encounter(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get encounter details"""
    
    try:
        encounter_uuid = uuid.UUID(encounter_id)
        encounter = db.query(Encounter).filter(
            Encounter.id == encounter_uuid,
            Encounter.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid encounter_id format")
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    return {
        "id": str(encounter.id),
        "patient_id": str(encounter.patient_id),
        "chief_complaint": encounter.chief_complaint,
        "encounter_date": encounter.encounter_date.isoformat(),
        "encounter_type": encounter.encounter_type,
        "status": encounter.status,
        "provider_name": encounter.provider_name,
        "location": encounter.location,
        "metadata": encounter.extra_metadata,
        "patient": {
            "id": str(encounter.patient.id),
            "mrn": encounter.patient.mrn,
            "first_name": encounter.patient.first_name,
            "last_name": encounter.patient.last_name
        }
    }


@router.put("/{encounter_id}")
async def update_encounter(
    encounter_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update encounter"""
    
    try:
        encounter_uuid = uuid.UUID(encounter_id)
        encounter = db.query(Encounter).filter(
            Encounter.id == encounter_uuid,
            Encounter.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid encounter_id format")
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update allowed fields
    if "chief_complaint" in update_data:
        encounter.chief_complaint = update_data["chief_complaint"]
    if "status" in update_data:
        encounter.status = update_data["status"]
    if "metadata" in update_data:
        encounter.extra_metadata = update_data["metadata"]
    
    encounter.updated_at = datetime.utcnow()
    db.commit()
    
    return {"updated": True}


@router.get("/")
async def list_encounters(
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List encounters"""
    
    query = db.query(Encounter).filter(Encounter.user_id == current_user.id)
    
    if patient_id:
        try:
            patient_uuid = uuid.UUID(patient_id)
            query = query.filter(Encounter.patient_id == patient_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient_id format")
    
    if status:
        query = query.filter(Encounter.status == status)
    
    # Order by most recent first
    query = query.order_by(Encounter.encounter_date.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    encounters = query.offset(skip).limit(limit).all()
    
    results = []
    for encounter in encounters:
        results.append({
            "id": str(encounter.id),
            "patient_id": str(encounter.patient_id),
            "chief_complaint": encounter.chief_complaint,
            "encounter_date": encounter.encounter_date.isoformat(),
            "encounter_type": encounter.encounter_type,
            "status": encounter.status,
            "provider_name": encounter.provider_name,
            "patient": {
                "mrn": encounter.patient.mrn,
                "first_name": encounter.patient.first_name,
                "last_name": encounter.patient.last_name
            }
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "encounters": results
    }