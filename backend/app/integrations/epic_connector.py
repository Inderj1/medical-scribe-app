import httpx
import jwt
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from .base import BaseEHRConnector, EHRCredentials, PatientData, EncounterData
from .fhir_client import FHIRClient

logger = logging.getLogger(__name__)


class EpicConnector(BaseEHRConnector):
    """Epic EHR connector using FHIR R4 API"""
    
    def __init__(self, credentials: EHRCredentials):
        super().__init__(credentials)
        self.fhir_client = FHIRClient(
            base_url=f"{credentials.base_url}/api/FHIR/R4",
            version="R4"
        )
        self.auth_endpoint = f"{credentials.base_url}/oauth2/token"
        
    async def authenticate(self) -> bool:
        """Authenticate with Epic using backend OAuth2"""
        try:
            # Create JWT assertion for backend authentication
            assertion = self._create_jwt_assertion()
            
            # Request access token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.auth_endpoint,
                    data={
                        'grant_type': 'client_credentials',
                        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                        'client_assertion': assertion,
                        'scope': 'system/Patient.read system/Encounter.read system/Observation.read system/Condition.read system/MedicationRequest.read system/AllergyIntolerance.read'
                    }
                )
                response.raise_for_status()
                
            token_data = response.json()
            self._access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("Successfully authenticated with Epic")
            return True
            
        except Exception as e:
            logger.error(f"Epic authentication failed: {e}")
            return False
            
    def _create_jwt_assertion(self) -> str:
        """Create JWT assertion for Epic backend authentication"""
        now = datetime.utcnow()
        
        claims = {
            'iss': self.credentials.client_id,
            'sub': self.credentials.client_id,
            'aud': self.auth_endpoint,
            'jti': str(now.timestamp()),
            'exp': int((now + timedelta(minutes=5)).timestamp()),
            'iat': int(now.timestamp())
        }
        
        # Sign with private key if available
        if self.credentials.private_key:
            private_key = load_pem_private_key(
                self.credentials.private_key.encode(),
                password=None
            )
            return jwt.encode(claims, private_key, algorithm='RS384')
        else:
            # Fallback to shared secret
            return jwt.encode(claims, self.credentials.client_secret, algorithm='HS256')
            
    async def get_patient(self, patient_id: str) -> PatientData:
        """Get patient information from Epic"""
        await self.ensure_authenticated()
        
        try:
            # Get patient resource
            patient_resource = await self.fhir_client.get_patient(
                patient_id, self._access_token
            )
            
            # Parse patient data
            parsed = self.fhir_client.parse_patient(patient_resource)
            
            # Get additional clinical data
            allergies = await self.get_allergies(patient_id)
            medications = await self.get_medications(patient_id)
            conditions = await self._get_conditions(patient_id)
            
            return PatientData(
                mrn=parsed['mrn'] or patient_id,
                first_name=parsed['first_name'],
                last_name=parsed['last_name'],
                date_of_birth=parsed['date_of_birth'],
                gender=parsed['gender'],
                phone=self._standardize_phone(parsed['phone']),
                email=parsed['email'],
                address=parsed['address'],
                allergies=allergies,
                medications=medications,
                conditions=conditions,
                ehr_id=patient_id
            )
            
        except Exception as e:
            logger.error(f"Failed to get patient from Epic: {e}")
            raise
            
    async def search_patients(self, **kwargs) -> List[PatientData]:
        """Search for patients in Epic"""
        await self.ensure_authenticated()
        
        try:
            # Add access token to kwargs
            kwargs['access_token'] = self._access_token
            
            # Search patients
            patients = await self.fhir_client.search_patients(**kwargs)
            
            # Convert to PatientData objects
            results = []
            for patient_resource in patients:
                parsed = self.fhir_client.parse_patient(patient_resource)
                results.append(PatientData(
                    mrn=parsed['mrn'] or parsed['id'],
                    first_name=parsed['first_name'],
                    last_name=parsed['last_name'],
                    date_of_birth=parsed['date_of_birth'],
                    gender=parsed['gender'],
                    phone=self._standardize_phone(parsed['phone']),
                    email=parsed['email'],
                    address=parsed['address'],
                    ehr_id=parsed['id']
                ))
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to search patients in Epic: {e}")
            raise
            
    async def get_encounter(self, encounter_id: str) -> EncounterData:
        """Get encounter information from Epic"""
        await self.ensure_authenticated()
        
        try:
            encounter_resource = await self.fhir_client.get_resource(
                "Encounter", encounter_id, self._access_token
            )
            
            parsed = self.fhir_client.parse_encounter(encounter_resource)
            
            # Get vitals for this encounter
            vitals = await self.get_vitals(
                parsed['patient_id'], 
                encounter_id
            )
            
            return EncounterData(
                encounter_id=encounter_id,
                encounter_date=datetime.fromisoformat(parsed['period'].get('start', '')),
                encounter_type=parsed['type'] or parsed['class'],
                location=parsed['location'],
                chief_complaint=' '.join(parsed['reason']),
                vitals=vitals
            )
            
        except Exception as e:
            logger.error(f"Failed to get encounter from Epic: {e}")
            raise
            
    async def get_patient_encounters(self, patient_id: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[EncounterData]:
        """Get patient encounters from Epic"""
        await self.ensure_authenticated()
        
        try:
            encounters = await self.fhir_client.get_encounters(
                patient_id,
                self._access_token,
                start_date.isoformat() if start_date else None,
                end_date.isoformat() if end_date else None
            )
            
            results = []
            for enc_resource in encounters:
                parsed = self.fhir_client.parse_encounter(enc_resource)
                
                if parsed['period'].get('start'):
                    results.append(EncounterData(
                        encounter_id=parsed['id'],
                        encounter_date=datetime.fromisoformat(parsed['period']['start']),
                        encounter_type=parsed['type'] or parsed['class'],
                        location=parsed['location'],
                        chief_complaint=' '.join(parsed['reason'])
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to get patient encounters from Epic: {e}")
            raise
            
    async def get_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient medications from Epic"""
        await self.ensure_authenticated()
        
        try:
            medications = await self.fhir_client.get_medications(
                patient_id, self._access_token
            )
            
            results = []
            for med in medications:
                medication_data = {
                    'name': self._extract_medication_name(med),
                    'status': med.get('status'),
                    'dosage': self._extract_dosage(med),
                    'route': self._extract_route(med),
                    'frequency': self._extract_frequency(med),
                    'start_date': med.get('authoredOn'),
                    'prescriber': self._extract_prescriber(med)
                }
                results.append(medication_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to get medications from Epic: {e}")
            raise
            
    async def get_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient allergies from Epic"""
        await self.ensure_authenticated()
        
        try:
            allergies = await self.fhir_client.get_allergies(
                patient_id, self._access_token
            )
            
            results = []
            for allergy in allergies:
                allergy_data = {
                    'substance': self._extract_allergen(allergy),
                    'reaction': self._extract_reactions(allergy),
                    'severity': allergy.get('criticality', 'unknown'),
                    'status': allergy.get('clinicalStatus', {}).get('coding', [{}])[0].get('code'),
                    'onset': allergy.get('onsetDateTime'),
                    'note': allergy.get('note', [{}])[0].get('text', '')
                }
                results.append(allergy_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to get allergies from Epic: {e}")
            raise
            
    async def get_lab_results(self, patient_id: str,
                            start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get patient lab results from Epic"""
        await self.ensure_authenticated()
        
        try:
            # Get laboratory observations
            labs = await self.fhir_client.get_observations(
                patient_id,
                self._access_token,
                category='laboratory'
            )
            
            results = []
            for lab in labs:
                if start_date and lab.get('effectiveDateTime'):
                    lab_date = datetime.fromisoformat(lab['effectiveDateTime'])
                    if lab_date < start_date:
                        continue
                        
                lab_data = {
                    'test_name': self._extract_observation_name(lab),
                    'value': self._extract_observation_value(lab),
                    'unit': self._extract_observation_unit(lab),
                    'reference_range': self._extract_reference_range(lab),
                    'status': lab.get('status'),
                    'date': lab.get('effectiveDateTime'),
                    'interpretation': self._extract_interpretation(lab)
                }
                results.append(lab_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to get lab results from Epic: {e}")
            raise
            
    async def get_vitals(self, patient_id: str,
                        encounter_id: Optional[str] = None) -> Dict[str, Any]:
        """Get patient vitals from Epic"""
        await self.ensure_authenticated()
        
        try:
            # Get vital signs observations
            vitals = await self.fhir_client.get_observations(
                patient_id,
                self._access_token,
                category='vital-signs'
            )
            
            # Filter by encounter if specified
            if encounter_id:
                vitals = [v for v in vitals 
                         if v.get('encounter', {}).get('reference', '').endswith(encounter_id)]
                         
            # Extract latest vitals
            vital_signs = {}
            vital_mapping = {
                '8480-6': 'blood_pressure_systolic',
                '8462-4': 'blood_pressure_diastolic',
                '8867-4': 'heart_rate',
                '9279-1': 'respiratory_rate',
                '8310-5': 'temperature',
                '59408-5': 'oxygen_saturation',
                '72514-3': 'pain_level'
            }
            
            for vital in vitals:
                code = self._extract_observation_code(vital)
                if code in vital_mapping:
                    vital_signs[vital_mapping[code]] = self._extract_observation_value(vital)
                    
            return vital_signs
            
        except Exception as e:
            logger.error(f"Failed to get vitals from Epic: {e}")
            raise
            
    async def _get_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient conditions/diagnoses from Epic"""
        try:
            conditions = await self.fhir_client.get_conditions(
                patient_id, self._access_token
            )
            
            results = []
            for condition in conditions:
                condition_data = {
                    'code': self._extract_condition_code(condition),
                    'display': self._extract_condition_display(condition),
                    'status': condition.get('clinicalStatus', {}).get('coding', [{}])[0].get('code'),
                    'onset': condition.get('onsetDateTime'),
                    'recorded': condition.get('recordedDate')
                }
                results.append(condition_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to get conditions from Epic: {e}")
            return []
            
    # Helper methods for extracting data from FHIR resources
    def _extract_medication_name(self, med_request: Dict[str, Any]) -> str:
        """Extract medication name from MedicationRequest"""
        if med_request.get('medicationCodeableConcept'):
            return med_request['medicationCodeableConcept'].get('text', 
                med_request['medicationCodeableConcept'].get('coding', [{}])[0].get('display', 'Unknown'))
        elif med_request.get('medicationReference'):
            return med_request['medicationReference'].get('display', 'Unknown')
        return 'Unknown'
        
    def _extract_dosage(self, med_request: Dict[str, Any]) -> str:
        """Extract dosage from MedicationRequest"""
        if med_request.get('dosageInstruction'):
            dosage = med_request['dosageInstruction'][0]
            if dosage.get('text'):
                return dosage['text']
            elif dosage.get('doseAndRate'):
                dose = dosage['doseAndRate'][0].get('doseQuantity', {})
                return f"{dose.get('value', '')} {dose.get('unit', '')}"
        return ''
        
    def _extract_route(self, med_request: Dict[str, Any]) -> str:
        """Extract route from MedicationRequest"""
        if med_request.get('dosageInstruction'):
            route = med_request['dosageInstruction'][0].get('route', {})
            return route.get('text', route.get('coding', [{}])[0].get('display', ''))
        return ''
        
    def _extract_frequency(self, med_request: Dict[str, Any]) -> str:
        """Extract frequency from MedicationRequest"""
        if med_request.get('dosageInstruction'):
            timing = med_request['dosageInstruction'][0].get('timing', {})
            if timing.get('code'):
                return timing['code'].get('text', '')
            elif timing.get('repeat'):
                repeat = timing['repeat']
                return f"{repeat.get('frequency', '')} times per {repeat.get('period', '')} {repeat.get('periodUnit', '')}"
        return ''
        
    def _extract_prescriber(self, med_request: Dict[str, Any]) -> str:
        """Extract prescriber from MedicationRequest"""
        if med_request.get('requester'):
            return med_request['requester'].get('display', '')
        return ''
        
    def _extract_allergen(self, allergy: Dict[str, Any]) -> str:
        """Extract allergen from AllergyIntolerance"""
        if allergy.get('code'):
            return allergy['code'].get('text',
                allergy['code'].get('coding', [{}])[0].get('display', 'Unknown'))
        return 'Unknown'
        
    def _extract_reactions(self, allergy: Dict[str, Any]) -> List[str]:
        """Extract reactions from AllergyIntolerance"""
        reactions = []
        for reaction in allergy.get('reaction', []):
            for manifestation in reaction.get('manifestation', []):
                reactions.append(manifestation.get('text',
                    manifestation.get('coding', [{}])[0].get('display', '')))
        return reactions
        
    def _extract_observation_name(self, observation: Dict[str, Any]) -> str:
        """Extract name from Observation"""
        if observation.get('code'):
            return observation['code'].get('text',
                observation['code'].get('coding', [{}])[0].get('display', 'Unknown'))
        return 'Unknown'
        
    def _extract_observation_code(self, observation: Dict[str, Any]) -> str:
        """Extract LOINC code from Observation"""
        if observation.get('code', {}).get('coding'):
            for coding in observation['code']['coding']:
                if coding.get('system') == 'http://loinc.org':
                    return coding.get('code', '')
        return ''
        
    def _extract_observation_value(self, observation: Dict[str, Any]) -> Any:
        """Extract value from Observation"""
        if observation.get('valueQuantity'):
            return observation['valueQuantity'].get('value')
        elif observation.get('valueCodeableConcept'):
            return observation['valueCodeableConcept'].get('text', '')
        elif observation.get('valueString'):
            return observation['valueString']
        return None
        
    def _extract_observation_unit(self, observation: Dict[str, Any]) -> str:
        """Extract unit from Observation"""
        if observation.get('valueQuantity'):
            return observation['valueQuantity'].get('unit', '')
        return ''
        
    def _extract_reference_range(self, observation: Dict[str, Any]) -> str:
        """Extract reference range from Observation"""
        if observation.get('referenceRange'):
            range_data = observation['referenceRange'][0]
            low = range_data.get('low', {}).get('value', '')
            high = range_data.get('high', {}).get('value', '')
            if low and high:
                return f"{low} - {high}"
        return ''
        
    def _extract_interpretation(self, observation: Dict[str, Any]) -> str:
        """Extract interpretation from Observation"""
        if observation.get('interpretation'):
            return observation['interpretation'][0].get('text',
                observation['interpretation'][0].get('coding', [{}])[0].get('display', ''))
        return ''
        
    def _extract_condition_code(self, condition: Dict[str, Any]) -> str:
        """Extract ICD code from Condition"""
        if condition.get('code', {}).get('coding'):
            for coding in condition['code']['coding']:
                if 'icd' in coding.get('system', '').lower():
                    return coding.get('code', '')
        return ''
        
    def _extract_condition_display(self, condition: Dict[str, Any]) -> str:
        """Extract display name from Condition"""
        if condition.get('code'):
            return condition['code'].get('text',
                condition['code'].get('coding', [{}])[0].get('display', 'Unknown'))
        return 'Unknown'