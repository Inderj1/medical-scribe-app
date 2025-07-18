from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EHRCredentials:
    """Base credentials for EHR authentication"""
    client_id: str
    client_secret: str
    base_url: str
    organization_id: Optional[str] = None
    private_key: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class PatientData:
    """Standardized patient data structure"""
    # Demographics
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    
    # Contact
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    
    # Clinical
    allergies: List[Dict[str, Any]] = None
    medications: List[Dict[str, Any]] = None
    conditions: List[Dict[str, Any]] = None
    immunizations: List[Dict[str, Any]] = None
    
    # Identifiers
    ehr_id: Optional[str] = None
    ssn: Optional[str] = None
    insurance_info: Optional[Dict[str, Any]] = None


@dataclass
class EncounterData:
    """Standardized encounter data structure"""
    encounter_id: str
    encounter_date: datetime
    encounter_type: str
    location: Optional[str] = None
    provider: Optional[Dict[str, str]] = None
    chief_complaint: Optional[str] = None
    diagnoses: List[Dict[str, Any]] = None
    procedures: List[Dict[str, Any]] = None
    vitals: Optional[Dict[str, Any]] = None


class BaseEHRConnector(ABC):
    """Abstract base class for EHR connectors"""
    
    def __init__(self, credentials: EHRCredentials):
        self.credentials = credentials
        self._access_token = None
        self._token_expiry = None
        self.ehr_name = self.__class__.__name__.replace('Connector', '')
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the EHR system"""
        pass
        
    @abstractmethod
    async def get_patient(self, patient_id: str) -> PatientData:
        """Retrieve patient information"""
        pass
        
    @abstractmethod
    async def search_patients(self, **kwargs) -> List[PatientData]:
        """Search for patients based on criteria"""
        pass
        
    @abstractmethod
    async def get_encounter(self, encounter_id: str) -> EncounterData:
        """Retrieve encounter information"""
        pass
        
    @abstractmethod
    async def get_patient_encounters(self, patient_id: str, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[EncounterData]:
        """Retrieve patient encounters within date range"""
        pass
        
    @abstractmethod
    async def get_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Retrieve patient medications"""
        pass
        
    @abstractmethod
    async def get_allergies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Retrieve patient allergies"""
        pass
        
    @abstractmethod
    async def get_lab_results(self, patient_id: str, 
                            start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve patient lab results"""
        pass
        
    @abstractmethod
    async def get_vitals(self, patient_id: str, 
                        encounter_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve patient vitals"""
        pass
        
    async def ensure_authenticated(self) -> None:
        """Ensure valid authentication before API calls"""
        if not self._access_token or self._is_token_expired():
            success = await self.authenticate()
            if not success:
                raise Exception(f"Failed to authenticate with {self.ehr_name}")
                
    def _is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self._token_expiry:
            return True
        return datetime.utcnow() >= self._token_expiry
        
    async def test_connection(self) -> bool:
        """Test EHR connection"""
        try:
            await self.authenticate()
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.ehr_name}: {e}")
            return False
            
    def _standardize_phone(self, phone: str) -> str:
        """Standardize phone number format"""
        if not phone:
            return None
        # Remove non-numeric characters
        cleaned = ''.join(filter(str.isdigit, phone))
        # Format as (XXX) XXX-XXXX if US number
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        return phone
        
    def _parse_address(self, address_data: Any) -> Dict[str, str]:
        """Parse address data into standard format"""
        # Override in subclasses for EHR-specific parsing
        return {
            "street": "",
            "city": "",
            "state": "",
            "zip": "",
            "country": "USA"
        }