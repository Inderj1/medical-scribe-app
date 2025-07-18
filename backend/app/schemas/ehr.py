from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.ehr_connection import EHRSystem


class EHRConnectionBase(BaseModel):
    organization_id: str
    organization_name: str
    ehr_system: EHRSystem
    base_url: str
    api_version: str = "R4"
    client_id: str
    tenant_id: Optional[str] = None
    is_sandbox: bool = False
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000


class EHRConnectionCreate(EHRConnectionBase):
    client_secret: str
    private_key: Optional[str] = None


class EHRConnectionUpdate(BaseModel):
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    private_key: Optional[str] = None
    is_active: Optional[bool] = None
    is_sandbox: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None


class EHRConnectionResponse(EHRConnectionBase):
    id: UUID4
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_tested_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EHRTestResponse(BaseModel):
    success: bool
    ehr_system: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PatientSearchParams(BaseModel):
    organization_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    mrn: Optional[str] = None
    phone: Optional[str] = None


class PatientSearchResponse(BaseModel):
    ehr_id: str
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: Optional[str] = None
    email: Optional[str] = None


class PatientSyncRequest(BaseModel):
    organization_id: str
    ehr_patient_id: str
    local_patient_id: Optional[str] = None
    sync_historical: bool = False


class PatientSyncResponse(BaseModel):
    success: bool
    patient_id: str
    mrn: str
    synced_data: Dict[str, Any]


class VitalsData(BaseModel):
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    pain_level: Optional[int] = None
    recorded_at: Optional[datetime] = None


class MedicationData(BaseModel):
    name: str
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: str = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prescriber: Optional[str] = None


class AllergyData(BaseModel):
    substance: str
    reaction: List[str] = []
    severity: str = "unknown"
    status: str = "active"
    onset: Optional[str] = None
    note: Optional[str] = None


class ConditionData(BaseModel):
    code: Optional[str] = None
    display: str
    status: str = "active"
    onset: Optional[str] = None
    recorded: Optional[str] = None


class LabResultData(BaseModel):
    test_name: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: str
    date: str
    interpretation: Optional[str] = None


class EncounterData(BaseModel):
    encounter_id: str
    encounter_date: datetime
    encounter_type: str
    location: Optional[str] = None
    provider: Optional[Dict[str, str]] = None
    chief_complaint: Optional[str] = None
    diagnoses: Optional[List[Dict[str, Any]]] = None
    procedures: Optional[List[Dict[str, Any]]] = None
    vitals: Optional[Dict[str, Any]] = None