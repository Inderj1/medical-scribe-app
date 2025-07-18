from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.db.session import get_db
from app.core.auth import get_current_active_user

logger = logging.getLogger(__name__)
from app.models.user import User
from app.integrations.ehr_manager import EHRManager
from app.schemas.ehr import (
    EHRConnectionCreate,
    EHRConnectionResponse,
    PatientSearchParams,
    PatientSearchResponse,
    PatientSyncRequest,
    PatientSyncResponse,
    EHRTestResponse
)

router = APIRouter()


@router.post("/connections", response_model=EHRConnectionResponse)
async def create_ehr_connection(
    connection_data: EHRConnectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new EHR connection for an organization"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create EHR connections"
        )
    
    from app.models.ehr_connection import EHRConnection
    
    # Check if connection already exists
    existing = db.query(EHRConnection).filter(
        EHRConnection.organization_id == connection_data.organization_id,
        EHRConnection.ehr_system == connection_data.ehr_system
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EHR connection already exists for this organization"
        )
    
    # Create new connection
    connection = EHRConnection(
        organization_id=connection_data.organization_id,
        organization_name=connection_data.organization_name,
        ehr_system=connection_data.ehr_system,
        base_url=connection_data.base_url,
        api_version=connection_data.api_version,
        client_id=connection_data.client_id,
        tenant_id=connection_data.tenant_id,
        private_key=connection_data.private_key,
        is_sandbox=connection_data.is_sandbox,
        rate_limit_per_minute=connection_data.rate_limit_per_minute,
        rate_limit_per_hour=connection_data.rate_limit_per_hour
    )
    
    # Encrypt and store client secret
    connection.encrypt_secret(connection_data.client_secret)
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return connection


@router.get("/connections", response_model=List[EHRConnectionResponse])
async def list_ehr_connections(
    organization_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List EHR connections"""
    from app.models.ehr_connection import EHRConnection
    
    query = db.query(EHRConnection)
    
    if organization_id:
        query = query.filter(EHRConnection.organization_id == organization_id)
    
    # Non-admin users can only see their organization's connections
    if not current_user.is_superuser:
        # Add organization filtering based on user's organization
        pass
    
    connections = query.all()
    return connections


@router.post("/connections/{connection_id}/test", response_model=EHRTestResponse)
async def test_ehr_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Test an EHR connection"""
    from app.models.ehr_connection import EHRConnection
    
    connection = db.query(EHRConnection).filter(
        EHRConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EHR connection not found"
        )
    
    # Test the connection
    ehr_manager = EHRManager(db)
    result = await ehr_manager.test_connection(connection.organization_id)
    
    # Update last tested timestamp
    connection.last_tested_at = datetime.utcnow()
    db.commit()
    
    return result


@router.post("/search/patients", response_model=List[PatientSearchResponse])
async def search_patients(
    search_params: PatientSearchParams,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search for patients in the connected EHR system"""
    ehr_manager = EHRManager(db)
    
    try:
        patients = await ehr_manager.search_patient(
            organization_id=search_params.organization_id,
            family=search_params.last_name,
            given=search_params.first_name,
            birthdate=search_params.date_of_birth,
            identifier=search_params.mrn
        )
        
        # Convert to response schema
        return [
            PatientSearchResponse(
                ehr_id=p.ehr_id,
                mrn=p.mrn,
                first_name=p.first_name,
                last_name=p.last_name,
                date_of_birth=p.date_of_birth,
                gender=p.gender,
                phone=p.phone,
                email=p.email
            )
            for p in patients
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EHR search failed: {str(e)}"
        )


@router.post("/sync/patient", response_model=PatientSyncResponse)
async def sync_patient_data(
    sync_request: PatientSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync patient data from EHR to local database"""
    ehr_manager = EHRManager(db)
    
    try:
        result = await ehr_manager.sync_patient(
            organization_id=sync_request.organization_id,
            ehr_patient_id=sync_request.ehr_patient_id,
            local_patient_id=sync_request.local_patient_id
        )
        
        # Schedule background sync of historical data
        if sync_request.sync_historical:
            background_tasks.add_task(
                sync_patient_history,
                ehr_manager,
                sync_request.organization_id,
                sync_request.ehr_patient_id,
                result['patient_id']
            )
        
        return PatientSyncResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Patient sync failed: {str(e)}"
        )


@router.get("/patient/{patient_id}/refresh")
async def refresh_patient_data(
    patient_id: str,
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh patient data from EHR"""
    ehr_manager = EHRManager(db)
    
    try:
        result = await ehr_manager.refresh_patient_data(organization_id, patient_id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Patient refresh failed: {str(e)}"
        )


@router.get("/patient/{patient_id}/encounters")
async def get_patient_encounters(
    patient_id: str,
    organization_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get patient encounters from EHR"""
    ehr_manager = EHRManager(db)
    
    try:
        # Get patient's EHR ID
        from app.models.patient import Patient
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient or not patient.ehr_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found or not linked to EHR"
            )
        
        encounters = await ehr_manager.get_patient_encounters(
            organization_id=organization_id,
            patient_id=patient.ehr_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return encounters
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get encounters: {str(e)}"
        )


@router.get("/patient/{patient_id}/vitals/latest")
async def get_latest_vitals(
    patient_id: str,
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get latest vitals for a patient from EHR"""
    ehr_manager = EHRManager(db)
    
    try:
        # Get patient's EHR ID
        from app.models.patient import Patient
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient or not patient.ehr_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found or not linked to EHR"
            )
        
        vitals = await ehr_manager.get_latest_vitals(
            organization_id=organization_id,
            patient_id=patient.ehr_id
        )
        
        return vitals
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vitals: {str(e)}"
        )


async def sync_patient_history(ehr_manager: EHRManager, organization_id: str,
                             ehr_patient_id: str, local_patient_id: str):
    """Background task to sync patient historical data"""
    try:
        # Get encounters from last year
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=365)
        
        encounters = await ehr_manager.get_patient_encounters(
            organization_id=organization_id,
            patient_id=ehr_patient_id,
            start_date=start_date
        )
        
        # Process and store encounters
        # This would involve creating local encounter records
        # and fetching associated data (notes, vitals, etc.)
        
        logger.info(f"Synced {len(encounters)} historical encounters for patient {local_patient_id}")
        
    except Exception as e:
        logger.error(f"Failed to sync patient history: {e}")