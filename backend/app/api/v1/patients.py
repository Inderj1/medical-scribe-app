"""Patients API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.services.ehrbase.client import EHRBaseClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync")
async def sync_patients_from_ehrbase(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync patients from EHRBase to local database"""
    client = EHRBaseClient()
    try:
        # Fetch all patients from EHRBase
        logger.info("Syncing patients from EHRBase...")
        ehr_patients = await client.get_all_patients()
        
        synced_count = 0
        updated_count = 0
        
        for ehr_patient in ehr_patients:
            # Extract patient data from EHRBase response format
            ehr_id = ehr_patient.get("ehr_id")
            patient_data = ehr_patient.get("patient", {})
            
            # Parse name - it comes as full name in EHRBase
            full_name = patient_data.get("name", "")
            name_parts = full_name.split(" ", 1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Extract external ref (MRN)
            external_ref = patient_data.get("external_ref", {})
            mrn = external_ref.get("id", f"MRN-{ehr_id[:8] if ehr_id else 'AUTO'}")
            
            # Check if patient already exists
            existing_patient = db.query(Patient).filter(
                Patient.ehr_id == ehr_id
            ).first()
            
            if not existing_patient:
                # Create new patient
                patient = Patient(
                    ehr_id=ehr_id,
                    mrn=mrn,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=patient_data.get("date_of_birth"),
                    gender=patient_data.get("gender", "").upper(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(patient)
                synced_count += 1
                logger.info(f"Created new patient: {full_name} (EHR ID: {ehr_id})")
            else:
                # Update existing patient
                existing_patient.first_name = first_name
                existing_patient.last_name = last_name
                existing_patient.gender = patient_data.get("gender", existing_patient.gender).upper() if patient_data.get("gender") else existing_patient.gender
                existing_patient.updated_at = datetime.utcnow()
                updated_count += 1
        
        db.commit()
        logger.info(f"Successfully synced {synced_count} new patients and updated {updated_count} existing patients from EHRBase")
        
        return {
            "message": f"Successfully synced {synced_count} new patients and updated {updated_count} existing patients",
            "total_patients": len(ehr_patients),
            "synced_count": synced_count,
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error syncing patients from EHRBase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/", response_model=List[dict])
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all patients from local database"""
    query = db.query(Patient)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Patient.first_name.ilike(search_term)) |
            (Patient.last_name.ilike(search_term)) |
            (Patient.mrn.ilike(search_term))
        )
    
    total = query.count()
    patients = query.offset(skip).limit(limit).all()
    
    # Convert to dict and add additional fields
    patient_list = []
    for patient in patients:
        patient_dict = {
            "id": str(patient.id),
            "ehr_id": patient.ehr_id,
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "phone": patient.phone,
            "email": patient.email,
            "age": patient.age,
            "full_name": f"{patient.first_name} {patient.last_name}"
        }
        
        # Get last encounter if exists
        last_encounter = db.query(Encounter).filter(
            Encounter.patient_id == patient.id
        ).order_by(Encounter.encounter_date.desc()).first()
        
        if last_encounter:
            patient_dict["last_visit"] = last_encounter.encounter_date.isoformat()
            patient_dict["last_provider"] = last_encounter.provider_name
        
        patient_list.append(patient_dict)
    
    return patient_list


@router.get("/search")
async def search_patients(
    q: Optional[str] = Query(None, description="Search query"),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    mrn: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search patients in local database and EHRBase"""
    
    # Build query for local database
    query = db.query(Patient)
    
    if q:
        # General search across multiple fields
        search_filter = or_(
            Patient.first_name.ilike(f"%{q}%"),
            Patient.last_name.ilike(f"%{q}%"),
            Patient.mrn.ilike(f"%{q}%")
        )
        query = query.filter(search_filter)
    else:
        # Specific field search
        if first_name:
            query = query.filter(Patient.first_name.ilike(f"%{first_name}%"))
        if last_name:
            query = query.filter(Patient.last_name.ilike(f"%{last_name}%"))
        if mrn:
            query = query.filter(Patient.mrn == mrn)
    
    # Get local results
    local_patients = query.limit(50).all()
    
    # Convert to dict format
    results = []
    for patient in local_patients:
        results.append({
            "id": str(patient.id),
            "ehr_id": patient.ehr_id,
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "phone": patient.phone,
            "email": patient.email,
            "source": "local"
        })
    
    # If few local results, also search EHRBase
    if len(results) < 10:
        try:
            ehrbase_client = EHRBaseClient()
            filters = {}
            if first_name:
                filters["firstName"] = first_name
            if last_name:
                filters["lastName"] = last_name
            if mrn:
                filters["mrn"] = mrn
                
            ehr_patients = await ehrbase_client.search_patients(filters)
            
            # Add EHR patients not in local DB
            local_mrns = {p["mrn"] for p in results}
            for ehr_patient in ehr_patients:
                if ehr_patient.get("mrn") not in local_mrns:
                    results.append({
                        **ehr_patient,
                        "source": "ehrbase"
                    })
                    
        except Exception as e:
            # Log error but don't fail the request
            print(f"EHRBase search error: {e}")
    
    return results


@router.post("/ensure")
async def ensure_patient_exists(
    patient_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Ensure patient exists in local database (create if not exists)"""
    
    # Try to find by EHR ID first
    ehr_id = patient_data.get("ehr_id")
    existing = None
    
    if ehr_id:
        existing = db.query(Patient).filter(Patient.ehr_id == ehr_id).first()
    
    # If not found by EHR ID, try MRN
    if not existing and patient_data.get("mrn"):
        existing = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
    
    if existing:
        # Update any missing fields
        if not existing.ehr_id and ehr_id:
            existing.ehr_id = ehr_id
        if patient_data.get("phone") and not existing.phone:
            existing.phone = patient_data["phone"]
        if patient_data.get("email") and not existing.email:
            existing.email = patient_data["email"]
        
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        
        return {
            "id": str(existing.id),
            "ehr_id": existing.ehr_id,
            "mrn": existing.mrn,
            "first_name": existing.first_name,
            "last_name": existing.last_name,
            "existed": True
        }
    
    # Create new patient
    patient = Patient(
        ehr_id=ehr_id,
        mrn=patient_data.get("mrn", f"MRN-{ehr_id[:8] if ehr_id else 'AUTO'}"),
        first_name=patient_data["first_name"],
        last_name=patient_data["last_name"],
        date_of_birth=patient_data.get("date_of_birth"),
        gender=patient_data.get("gender", "").upper() if patient_data.get("gender") else None,
        phone=patient_data.get("phone"),
        email=patient_data.get("email"),
        address=patient_data.get("address")
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return {
        "id": str(patient.id),
        "ehr_id": patient.ehr_id,
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "created": True
    }


@router.post("/")
async def create_patient(
    patient_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new patient"""
    
    # Check if patient with MRN already exists
    existing = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this MRN already exists")
    
    # Create patient
    patient = Patient(
        mrn=patient_data["mrn"],
        first_name=patient_data["first_name"],
        last_name=patient_data["last_name"],
        date_of_birth=patient_data.get("date_of_birth"),
        gender=patient_data.get("gender"),
        phone=patient_data.get("phone"),
        email=patient_data.get("email"),
        address=patient_data.get("address")
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    # Try to create in EHRBase as well
    try:
        ehrbase_client = EHRBaseClient()
        # Create EHR in EHRBase if needed
        # ehr_id = await ehrbase_client.create_ehr(patient_data)
        # patient.ehr_id = ehr_id
        # db.commit()
    except Exception as e:
        print(f"EHRBase creation error: {e}")
    
    return {
        "id": str(patient.id),
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "created": True
    }


@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get patient details"""
    
    # Try to parse as UUID
    try:
        patient_uuid = uuid.UUID(patient_id)
        patient = db.query(Patient).filter(Patient.id == patient_uuid).first()
    except ValueError:
        # Not a UUID, try as MRN
        patient = db.query(Patient).filter(Patient.mrn == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get additional data from EHRBase if available
    ehr_data = {}
    if patient.ehr_id:
        try:
            ehrbase_client = EHRBaseClient()
            ehr_data = await ehrbase_client.get_patient_summary(patient.ehr_id)
        except Exception as e:
            print(f"EHRBase fetch error: {e}")
    
    return {
        "id": str(patient.id),
        "ehr_id": patient.ehr_id,
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "gender": patient.gender,
        "phone": patient.phone,
        "email": patient.email,
        "address": patient.address,
        "insurance_info": patient.insurance_info,
        "emergency_contact": patient.emergency_contact,
        **ehr_data
    }


@router.get("/{patient_id}/records")
async def get_patient_records(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get patient medical records from EHRBase"""
    
    # Get patient
    try:
        patient_uuid = uuid.UUID(patient_id)
        patient = db.query(Patient).filter(Patient.id == patient_uuid).first()
    except ValueError:
        patient = db.query(Patient).filter(Patient.mrn == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if not patient.ehr_id:
        return []
    
    # Get records from EHRBase
    try:
        ehrbase_client = EHRBaseClient()
        records = await ehrbase_client.get_patient_records(patient.ehr_id)
        return records
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []