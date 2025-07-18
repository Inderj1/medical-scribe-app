import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import urlencode

from .base import BaseEHRConnector, EHRCredentials, PatientData, EncounterData
from .fhir_client import FHIRClient

logger = logging.getLogger(__name__)


class CernerConnector(BaseEHRConnector):
    """Cerner EHR connector using SMART on FHIR"""
    
    def __init__(self, credentials: EHRCredentials):
        super().__init__(credentials)
        self.fhir_client = FHIRClient(
            base_url=f"{credentials.base_url}/api/FHIR/DSTU2",  # Cerner primarily uses DSTU2
            version="DSTU2"
        )
        self.auth_endpoint = f"{credentials.base_url}/auth/oauth/v2/token"
        
    async def authenticate(self) -> bool:
        """Authenticate with Cerner using client credentials"""
        try:
            async with httpx.AsyncClient() as client:
                # Cerner uses Basic Auth for client credentials
                response = await client.post(
                    self.auth_endpoint,
                    auth=(self.credentials.client_id, self.credentials.client_secret),
                    data={
                        'grant_type': 'client_credentials',
                        'scope': 'system/Patient.read system/Encounter.read system/Observation.read'
                    }
                )
                response.raise_for_status()
                
            token_data = response.json()
            self._access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("Successfully authenticated with Cerner")
            return True
            
        except Exception as e:
            logger.error(f"Cerner authentication failed: {e}")
            return False
            
    async def get_patient(self, patient_id: str) -> PatientData:
        """Get patient information from Cerner"""
        await self.ensure_authenticated()
        
        try:
            # Cerner requires specific headers
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            # Get patient resource
            url = f"{self.credentials.base_url}/Patient/{patient_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                patient_resource = response.json()
                
            # Parse patient data
            parsed = self._parse_cerner_patient(patient_resource)
            
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
            logger.error(f"Failed to get patient from Cerner: {e}")
            raise
            
    async def search_patients(self, **kwargs) -> List[PatientData]:
        """Search for patients in Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            # Build search parameters
            params = []
            if 'family' in kwargs:
                params.append(f"family={kwargs['family']}")
            if 'given' in kwargs:
                params.append(f"given={kwargs['given']}")
            if 'birthdate' in kwargs:
                params.append(f"birthdate={kwargs['birthdate']}")
            if 'identifier' in kwargs:
                params.append(f"identifier={kwargs['identifier']}")
                
            url = f"{self.credentials.base_url}/Patient"
            if params:
                url += f"?{urlencode(params)}"
                
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            # Extract patients from bundle
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    parsed = self._parse_cerner_patient(entry['resource'])
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
            logger.error(f"Failed to search patients in Cerner: {e}")
            raise
            
    async def get_encounter(self, encounter_id: str) -> EncounterData:
        """Get encounter information from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            url = f"{self.credentials.base_url}/Encounter/{encounter_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                encounter_resource = response.json()
                
            parsed = self._parse_cerner_encounter(encounter_resource)
            
            # Get vitals for this encounter
            patient_id = parsed['patient_id']
            vitals = await self.get_vitals(patient_id, encounter_id)
            
            return EncounterData(
                encounter_id=encounter_id,
                encounter_date=datetime.fromisoformat(parsed['period'].get('start', '')),
                encounter_type=parsed['type'] or parsed['class'],
                location=parsed['location'],
                chief_complaint=' '.join(parsed['reason']),
                vitals=vitals
            )
            
        except Exception as e:
            logger.error(f"Failed to get encounter from Cerner: {e}")
            raise
            
    async def get_patient_encounters(self, patient_id: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[EncounterData]:
        """Get patient encounters from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            params = [f"patient={patient_id}"]
            if start_date:
                params.append(f"date=ge{start_date.strftime('%Y-%m-%d')}")
            if end_date:
                params.append(f"date=le{end_date.strftime('%Y-%m-%d')}")
                
            url = f"{self.credentials.base_url}/Encounter?{urlencode(params)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    parsed = self._parse_cerner_encounter(entry['resource'])
                    
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
            logger.error(f"Failed to get patient encounters from Cerner: {e}")
            raise
            
    async def get_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient medications from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            # Cerner uses MedicationOrder in DSTU2
            url = f"{self.credentials.base_url}/MedicationOrder?patient={patient_id}&status=active"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    med = entry['resource']
                    medication_data = {
                        'name': self._extract_cerner_medication_name(med),
                        'status': med.get('status'),
                        'dosage': self._extract_cerner_dosage(med),
                        'route': med.get('dosageInstruction', [{}])[0].get('route', {}).get('text', ''),
                        'frequency': med.get('dosageInstruction', [{}])[0].get('timing', {}).get('code', {}).get('text', ''),
                        'start_date': med.get('dateWritten'),
                        'prescriber': med.get('prescriber', {}).get('display', '')
                    }
                    results.append(medication_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to get medications from Cerner: {e}")
            raise
            
    async def get_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient allergies from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            url = f"{self.credentials.base_url}/AllergyIntolerance?patient={patient_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    allergy = entry['resource']
                    allergy_data = {
                        'substance': allergy.get('substance', {}).get('text', 'Unknown'),
                        'reaction': [r.get('manifestation', [{}])[0].get('text', '') 
                                   for r in allergy.get('reaction', [])],
                        'severity': allergy.get('criticality', 'unknown'),
                        'status': allergy.get('status', 'active'),
                        'onset': allergy.get('onset'),
                        'note': allergy.get('note', {}).get('text', '')
                    }
                    results.append(allergy_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to get allergies from Cerner: {e}")
            raise
            
    async def get_lab_results(self, patient_id: str,
                            start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get patient lab results from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            params = [f"patient={patient_id}", "category=laboratory"]
            if start_date:
                params.append(f"date=ge{start_date.strftime('%Y-%m-%d')}")
                
            url = f"{self.credentials.base_url}/Observation?{urlencode(params)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    lab = entry['resource']
                    lab_data = {
                        'test_name': lab.get('code', {}).get('text', 'Unknown'),
                        'value': self._extract_cerner_observation_value(lab),
                        'unit': lab.get('valueQuantity', {}).get('unit', ''),
                        'reference_range': self._extract_cerner_reference_range(lab),
                        'status': lab.get('status'),
                        'date': lab.get('effectiveDateTime'),
                        'interpretation': lab.get('interpretation', {}).get('text', '')
                    }
                    results.append(lab_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to get lab results from Cerner: {e}")
            raise
            
    async def get_vitals(self, patient_id: str,
                        encounter_id: Optional[str] = None) -> Dict[str, Any]:
        """Get patient vitals from Cerner"""
        await self.ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            params = [f"patient={patient_id}", "category=vital-signs"]
            if encounter_id:
                params.append(f"context={encounter_id}")
                
            url = f"{self.credentials.base_url}/Observation?{urlencode(params)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            # Extract latest vitals
            vital_signs = {}
            vital_mapping = {
                '8480-6': 'blood_pressure_systolic',
                '8462-4': 'blood_pressure_diastolic',
                '8867-4': 'heart_rate',
                '9279-1': 'respiratory_rate',
                '8310-5': 'temperature',
                '2710-2': 'oxygen_saturation',  # Cerner sometimes uses different code
                '72514-3': 'pain_level'
            }
            
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    vital = entry['resource']
                    code = self._extract_cerner_loinc_code(vital)
                    
                    if code in vital_mapping:
                        value = self._extract_cerner_observation_value(vital)
                        if value is not None:
                            vital_signs[vital_mapping[code]] = value
                            
            return vital_signs
            
        except Exception as e:
            logger.error(f"Failed to get vitals from Cerner: {e}")
            raise
            
    async def _get_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient conditions/diagnoses from Cerner"""
        try:
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json+fhir'
            }
            
            url = f"{self.credentials.base_url}/Condition?patient={patient_id}&clinicalstatus=active"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                
            results = []
            for entry in bundle.get('entry', []):
                if 'resource' in entry:
                    condition = entry['resource']
                    condition_data = {
                        'code': condition.get('code', {}).get('coding', [{}])[0].get('code', ''),
                        'display': condition.get('code', {}).get('text', 'Unknown'),
                        'status': condition.get('clinicalStatus', 'active'),
                        'onset': condition.get('onsetDateTime'),
                        'recorded': condition.get('dateRecorded')
                    }
                    results.append(condition_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to get conditions from Cerner: {e}")
            return []
            
    # Cerner-specific parsing methods
    def _parse_cerner_patient(self, patient_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Cerner Patient resource"""
        data = {
            'id': patient_resource.get('id'),
            'mrn': None,
            'first_name': '',
            'last_name': '',
            'date_of_birth': patient_resource.get('birthDate'),
            'gender': patient_resource.get('gender', 'unknown'),
            'phone': None,
            'email': None,
            'address': None
        }
        
        # Parse identifiers for MRN
        for identifier in patient_resource.get('identifier', []):
            if identifier.get('type', {}).get('coding', [{}])[0].get('code') == 'MR':
                data['mrn'] = identifier.get('value')
                break
                
        # Parse name
        if patient_resource.get('name'):
            name = patient_resource['name'][0]
            data['first_name'] = ' '.join(name.get('given', []))
            data['last_name'] = name.get('family', [''])[0]  # DSTU2 uses array
            
        # Parse telecom
        for telecom in patient_resource.get('telecom', []):
            if telecom.get('system') == 'phone':
                data['phone'] = telecom.get('value')
            elif telecom.get('system') == 'email':
                data['email'] = telecom.get('value')
                
        # Parse address
        if patient_resource.get('address'):
            addr = patient_resource['address'][0]
            data['address'] = {
                'street': ' '.join(addr.get('line', [])),
                'city': addr.get('city', ''),
                'state': addr.get('state', ''),
                'zip': addr.get('postalCode', ''),
                'country': addr.get('country', 'USA')
            }
            
        return data
        
    def _parse_cerner_encounter(self, encounter_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Cerner Encounter resource"""
        data = {
            'id': encounter_resource.get('id'),
            'status': encounter_resource.get('status'),
            'class': encounter_resource.get('class'),
            'type': None,
            'patient_id': None,
            'period': encounter_resource.get('period', {}),
            'location': None,
            'reason': []
        }
        
        # Parse encounter type
        if encounter_resource.get('type'):
            data['type'] = encounter_resource['type'][0].get('text', '')
            
        # Parse patient reference
        if encounter_resource.get('patient', {}).get('reference'):
            data['patient_id'] = encounter_resource['patient']['reference'].split('/')[-1]
            
        # Parse location
        if encounter_resource.get('location'):
            data['location'] = encounter_resource['location'][0].get('location', {}).get('display', '')
            
        # Parse reason
        for reason in encounter_resource.get('reason', []):
            data['reason'].append(reason.get('text', ''))
            
        return data
        
    def _extract_cerner_medication_name(self, med_order: Dict[str, Any]) -> str:
        """Extract medication name from Cerner MedicationOrder"""
        if med_order.get('medicationCodeableConcept'):
            return med_order['medicationCodeableConcept'].get('text', 'Unknown')
        elif med_order.get('medicationReference'):
            return med_order['medicationReference'].get('display', 'Unknown')
        return 'Unknown'
        
    def _extract_cerner_dosage(self, med_order: Dict[str, Any]) -> str:
        """Extract dosage from Cerner MedicationOrder"""
        if med_order.get('dosageInstruction'):
            dosage = med_order['dosageInstruction'][0]
            if dosage.get('text'):
                return dosage['text']
            elif dosage.get('doseQuantity'):
                dose = dosage['doseQuantity']
                return f"{dose.get('value', '')} {dose.get('unit', '')}"
        return ''
        
    def _extract_cerner_observation_value(self, observation: Dict[str, Any]) -> Any:
        """Extract value from Cerner Observation"""
        if observation.get('valueQuantity'):
            return observation['valueQuantity'].get('value')
        elif observation.get('valueCodeableConcept'):
            return observation['valueCodeableConcept'].get('text', '')
        elif observation.get('valueString'):
            return observation['valueString']
        # Handle blood pressure as components
        elif observation.get('component'):
            for component in observation['component']:
                code = component.get('code', {}).get('coding', [{}])[0].get('code', '')
                if code == '8480-6':  # Systolic
                    return component.get('valueQuantity', {}).get('value')
        return None
        
    def _extract_cerner_reference_range(self, observation: Dict[str, Any]) -> str:
        """Extract reference range from Cerner Observation"""
        if observation.get('referenceRange'):
            range_data = observation['referenceRange'][0]
            low = range_data.get('low', {}).get('value', '')
            high = range_data.get('high', {}).get('value', '')
            if low and high:
                return f"{low} - {high}"
            elif range_data.get('text'):
                return range_data['text']
        return ''
        
    def _extract_cerner_loinc_code(self, observation: Dict[str, Any]) -> str:
        """Extract LOINC code from Cerner Observation"""
        if observation.get('code', {}).get('coding'):
            for coding in observation['code']['coding']:
                if 'loinc' in coding.get('system', '').lower():
                    return coding.get('code', '')
        return ''