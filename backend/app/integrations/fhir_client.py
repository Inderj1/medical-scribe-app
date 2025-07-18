import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from urllib.parse import urljoin, urlencode

logger = logging.getLogger(__name__)


class FHIRClient:
    """Generic FHIR client for EHR integration"""
    
    def __init__(self, base_url: str, version: str = "R4"):
        self.base_url = base_url.rstrip('/')
        self.version = version
        self.session = httpx.AsyncClient(timeout=30.0)
        
    async def get_resource(self, resource_type: str, resource_id: str, 
                          access_token: str) -> Dict[str, Any]:
        """Get a single FHIR resource"""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        headers = self._get_headers(access_token)
        
        try:
            response = await self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get {resource_type}/{resource_id}: {e}")
            raise
            
    async def search_resource(self, resource_type: str, params: Dict[str, str],
                            access_token: str) -> Dict[str, Any]:
        """Search for FHIR resources"""
        url = f"{self.base_url}/{resource_type}"
        headers = self._get_headers(access_token)
        
        try:
            response = await self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to search {resource_type}: {e}")
            raise
            
    async def get_patient(self, patient_id: str, access_token: str) -> Dict[str, Any]:
        """Get patient resource"""
        return await self.get_resource("Patient", patient_id, access_token)
        
    async def search_patients(self, **kwargs) -> List[Dict[str, Any]]:
        """Search for patients with various criteria"""
        params = {}
        
        # Map common search parameters
        if 'family' in kwargs:
            params['family'] = kwargs['family']
        if 'given' in kwargs:
            params['given'] = kwargs['given']
        if 'birthdate' in kwargs:
            params['birthdate'] = kwargs['birthdate']
        if 'identifier' in kwargs:
            params['identifier'] = kwargs['identifier']
        if 'name' in kwargs:
            params['name'] = kwargs['name']
            
        bundle = await self.search_resource("Patient", params, kwargs.get('access_token'))
        return self._extract_resources_from_bundle(bundle)
        
    async def get_patient_everything(self, patient_id: str, access_token: str,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get all patient data using $everything operation"""
        url = f"{self.base_url}/Patient/{patient_id}/$everything"
        headers = self._get_headers(access_token)
        params = {}
        
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
            
        try:
            response = await self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get patient everything: {e}")
            raise
            
    async def get_encounters(self, patient_id: str, access_token: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patient encounters"""
        params = {
            'patient': patient_id,
            '_sort': '-date'
        }
        
        if start_date:
            params['date'] = f'ge{start_date}'
        if end_date:
            if 'date' in params:
                params['date'] = f'{params["date"]}&le{end_date}'
            else:
                params['date'] = f'le{end_date}'
                
        bundle = await self.search_resource("Encounter", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    async def get_conditions(self, patient_id: str, access_token: str) -> List[Dict[str, Any]]:
        """Get patient conditions/diagnoses"""
        params = {
            'patient': patient_id,
            'clinical-status': 'active'
        }
        
        bundle = await self.search_resource("Condition", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    async def get_medications(self, patient_id: str, access_token: str) -> List[Dict[str, Any]]:
        """Get patient medications"""
        params = {
            'patient': patient_id,
            'status': 'active'
        }
        
        bundle = await self.search_resource("MedicationRequest", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    async def get_allergies(self, patient_id: str, access_token: str) -> List[Dict[str, Any]]:
        """Get patient allergies"""
        params = {
            'patient': patient_id,
            'clinical-status': 'active'
        }
        
        bundle = await self.search_resource("AllergyIntolerance", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    async def get_observations(self, patient_id: str, access_token: str,
                             category: Optional[str] = None,
                             code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patient observations (vitals, lab results)"""
        params = {
            'patient': patient_id,
            '_sort': '-date'
        }
        
        if category:
            params['category'] = category
        if code:
            params['code'] = code
            
        bundle = await self.search_resource("Observation", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    async def get_immunizations(self, patient_id: str, access_token: str) -> List[Dict[str, Any]]:
        """Get patient immunizations"""
        params = {
            'patient': patient_id
        }
        
        bundle = await self.search_resource("Immunization", params, access_token)
        return self._extract_resources_from_bundle(bundle)
        
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get standard headers for FHIR requests"""
        return {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json'
        }
        
    def _extract_resources_from_bundle(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract resources from FHIR bundle"""
        if bundle.get('resourceType') != 'Bundle':
            return []
            
        resources = []
        for entry in bundle.get('entry', []):
            if 'resource' in entry:
                resources.append(entry['resource'])
                
        return resources
        
    def parse_patient(self, patient_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR Patient resource into standard format"""
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
            data['last_name'] = name.get('family', '')
            
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
        
    def parse_encounter(self, encounter_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR Encounter resource into standard format"""
        data = {
            'id': encounter_resource.get('id'),
            'status': encounter_resource.get('status'),
            'class': encounter_resource.get('class', {}).get('code'),
            'type': None,
            'patient_id': None,
            'period': encounter_resource.get('period', {}),
            'location': None,
            'reason': []
        }
        
        # Parse encounter type
        if encounter_resource.get('type'):
            data['type'] = encounter_resource['type'][0].get('text', 
                encounter_resource['type'][0].get('coding', [{}])[0].get('display'))
            
        # Parse patient reference
        if encounter_resource.get('subject', {}).get('reference'):
            data['patient_id'] = encounter_resource['subject']['reference'].split('/')[-1]
            
        # Parse location
        if encounter_resource.get('location'):
            location_ref = encounter_resource['location'][0].get('location', {}).get('display')
            data['location'] = location_ref
            
        # Parse reason for visit
        for reason in encounter_resource.get('reasonCode', []):
            data['reason'].append(reason.get('text', 
                reason.get('coding', [{}])[0].get('display')))
                
        return data
        
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()