from typing import Dict, Any, List, Optional, Type
from enum import Enum
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from .base import BaseEHRConnector, EHRCredentials, PatientData, EncounterData
from .epic_connector import EpicConnector
from .cerner_connector import CernerConnector
from ..models.ehr_connection import EHRConnection, EHRSystem
from ..core.config import settings

logger = logging.getLogger(__name__)


class EHRManager:
    """Manages connections to multiple EHR systems"""
    
    # Registry of available connectors
    CONNECTORS: Dict[EHRSystem, Type[BaseEHRConnector]] = {
        EHRSystem.EPIC: EpicConnector,
        EHRSystem.CERNER: CernerConnector,
        # Add more connectors as implemented
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._connectors: Dict[str, BaseEHRConnector] = {}
        
    async def get_connector(self, organization_id: str) -> BaseEHRConnector:
        """Get or create a connector for an organization"""
        if organization_id in self._connectors:
            return self._connectors[organization_id]
            
        # Get EHR connection details from database
        connection = self.db.query(EHRConnection).filter(
            EHRConnection.organization_id == organization_id,
            EHRConnection.is_active == True
        ).first()
        
        if not connection:
            raise ValueError(f"No active EHR connection found for organization {organization_id}")
            
        # Create appropriate connector
        connector_class = self.CONNECTORS.get(connection.ehr_system)
        if not connector_class:
            raise ValueError(f"No connector available for {connection.ehr_system}")
            
        # Build credentials
        credentials = EHRCredentials(
            client_id=connection.client_id,
            client_secret=connection.decrypt_secret(),  # Decrypt stored secret
            base_url=connection.base_url,
            organization_id=organization_id,
            private_key=connection.private_key,
            tenant_id=connection.tenant_id
        )
        
        # Create and cache connector
        connector = connector_class(credentials)
        self._connectors[organization_id] = connector
        
        return connector
        
    async def test_connection(self, organization_id: str) -> Dict[str, Any]:
        """Test EHR connection for an organization"""
        try:
            connector = await self.get_connector(organization_id)
            success = await connector.test_connection()
            
            return {
                'success': success,
                'ehr_system': connector.ehr_name,
                'message': 'Connection successful' if success else 'Connection failed'
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def search_patient(self, organization_id: str, **search_params) -> List[PatientData]:
        """Search for patients across the organization's EHR"""
        try:
            connector = await self.get_connector(organization_id)
            return await connector.search_patients(**search_params)
        except Exception as e:
            logger.error(f"Patient search failed: {e}")
            raise
            
    async def get_patient_data(self, organization_id: str, patient_id: str) -> PatientData:
        """Get comprehensive patient data"""
        try:
            connector = await self.get_connector(organization_id)
            return await connector.get_patient(patient_id)
        except Exception as e:
            logger.error(f"Failed to get patient data: {e}")
            raise
            
    async def sync_patient(self, organization_id: str, ehr_patient_id: str,
                          local_patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Sync patient data from EHR to local database"""
        try:
            connector = await self.get_connector(organization_id)
            
            # Get patient data from EHR
            patient_data = await connector.get_patient(ehr_patient_id)
            
            # Update or create local patient record
            from ..models.patient import Patient
            
            if local_patient_id:
                patient = self.db.query(Patient).filter(
                    Patient.id == local_patient_id
                ).first()
            else:
                # Try to find by MRN
                patient = self.db.query(Patient).filter(
                    Patient.mrn == patient_data.mrn
                ).first()
                
            if patient:
                # Update existing patient
                patient.first_name = patient_data.first_name
                patient.last_name = patient_data.last_name
                patient.date_of_birth = patient_data.date_of_birth
                patient.gender = patient_data.gender
                patient.phone = patient_data.phone
                patient.email = patient_data.email
                patient.ehr_id = ehr_patient_id
            else:
                # Create new patient
                patient = Patient(
                    mrn=patient_data.mrn,
                    first_name=patient_data.first_name,
                    last_name=patient_data.last_name,
                    date_of_birth=patient_data.date_of_birth,
                    gender=patient_data.gender,
                    phone=patient_data.phone,
                    email=patient_data.email,
                    ehr_id=ehr_patient_id
                )
                self.db.add(patient)
                
            self.db.commit()
            
            # Store clinical data in separate tables
            await self._sync_allergies(patient.id, patient_data.allergies)
            await self._sync_medications(patient.id, patient_data.medications)
            await self._sync_conditions(patient.id, patient_data.conditions)
            
            return {
                'success': True,
                'patient_id': str(patient.id),
                'mrn': patient.mrn,
                'synced_data': {
                    'demographics': True,
                    'allergies': len(patient_data.allergies or []),
                    'medications': len(patient_data.medications or []),
                    'conditions': len(patient_data.conditions or [])
                }
            }
            
        except Exception as e:
            logger.error(f"Patient sync failed: {e}")
            self.db.rollback()
            raise
            
    async def get_patient_encounters(self, organization_id: str, patient_id: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[EncounterData]:
        """Get patient encounters from EHR"""
        try:
            connector = await self.get_connector(organization_id)
            return await connector.get_patient_encounters(patient_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to get encounters: {e}")
            raise
            
    async def get_latest_vitals(self, organization_id: str, patient_id: str) -> Dict[str, Any]:
        """Get latest vitals for a patient"""
        try:
            connector = await self.get_connector(organization_id)
            return await connector.get_vitals(patient_id)
        except Exception as e:
            logger.error(f"Failed to get vitals: {e}")
            raise
            
    async def refresh_patient_data(self, organization_id: str, local_patient_id: str) -> Dict[str, Any]:
        """Refresh patient data from EHR"""
        try:
            # Get patient with EHR ID
            from ..models.patient import Patient
            patient = self.db.query(Patient).filter(
                Patient.id == local_patient_id
            ).first()
            
            if not patient or not patient.ehr_id:
                raise ValueError("Patient not found or not linked to EHR")
                
            # Sync latest data
            return await self.sync_patient(organization_id, patient.ehr_id, local_patient_id)
            
        except Exception as e:
            logger.error(f"Failed to refresh patient data: {e}")
            raise
            
    async def _sync_allergies(self, patient_id: str, allergies: List[Dict[str, Any]]) -> None:
        """Sync patient allergies to local database"""
        if not allergies:
            return
            
        from ..models.patient_allergy import PatientAllergy
        
        # Clear existing allergies
        self.db.query(PatientAllergy).filter(
            PatientAllergy.patient_id == patient_id
        ).delete()
        
        # Add new allergies
        for allergy in allergies:
            allergy_record = PatientAllergy(
                patient_id=patient_id,
                substance=allergy.get('substance'),
                reaction=' '.join(allergy.get('reaction', [])),
                severity=allergy.get('severity'),
                status=allergy.get('status'),
                onset_date=allergy.get('onset'),
                note=allergy.get('note')
            )
            self.db.add(allergy_record)
            
        self.db.commit()
        
    async def _sync_medications(self, patient_id: str, medications: List[Dict[str, Any]]) -> None:
        """Sync patient medications to local database"""
        if not medications:
            return
            
        from ..models.patient_medication import PatientMedication
        
        # Clear existing medications
        self.db.query(PatientMedication).filter(
            PatientMedication.patient_id == patient_id
        ).delete()
        
        # Add new medications
        for med in medications:
            med_record = PatientMedication(
                patient_id=patient_id,
                name=med.get('name'),
                dosage=med.get('dosage'),
                route=med.get('route'),
                frequency=med.get('frequency'),
                status=med.get('status'),
                start_date=med.get('start_date'),
                prescriber=med.get('prescriber')
            )
            self.db.add(med_record)
            
        self.db.commit()
        
    async def _sync_conditions(self, patient_id: str, conditions: List[Dict[str, Any]]) -> None:
        """Sync patient conditions to local database"""
        if not conditions:
            return
            
        from ..models.patient_condition import PatientCondition
        
        # Clear existing conditions
        self.db.query(PatientCondition).filter(
            PatientCondition.patient_id == patient_id
        ).delete()
        
        # Add new conditions
        for condition in conditions:
            condition_record = PatientCondition(
                patient_id=patient_id,
                code=condition.get('code'),
                display=condition.get('display'),
                status=condition.get('status'),
                onset_date=condition.get('onset'),
                recorded_date=condition.get('recorded')
            )
            self.db.add(condition_record)
            
        self.db.commit()
        
    def clear_cache(self, organization_id: Optional[str] = None) -> None:
        """Clear cached connectors"""
        if organization_id:
            self._connectors.pop(organization_id, None)
        else:
            self._connectors.clear()