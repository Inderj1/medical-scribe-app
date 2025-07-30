"""EHRBase Client for medical record integration"""
import httpx
from typing import Optional, Dict, Any, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EHRBaseClient:
    """Client for interacting with EHRBase API"""
    
    def __init__(self):
        self.base_url = "http://3.223.44.85"  # Use the actual EHRBase URL
        # Create both sync and async clients
        self.async_client = httpx.AsyncClient(timeout=30.0)
        self.sync_client = httpx.Client(timeout=30.0)
        
        # Auth headers if needed
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if settings.EHRBASE_USERNAME and settings.EHRBASE_PASSWORD:
            # Add basic auth or other auth mechanism
            pass
    
    async def get_all_patients(self) -> List[Dict]:
        """Get all patients from EHRBase"""
        try:
            response = await self.async_client.get(
                f"{self.base_url}/api/patients",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            # The API returns a dict with "patients" key containing the list
            if isinstance(data, dict) and "patients" in data:
                return data["patients"]
            return []
                
        except Exception as e:
            logger.error(f"Error fetching patients: {str(e)}")
            return []
    
    async def get_patient_records(self, patient_id: str) -> List[Dict]:
        """Get all records for a patient"""
        try:
            response = await self.async_client.get(
                f"{self.base_url}/api/patients/{patient_id}/records",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting patient records: {str(e)}")
            return []
    
    async def get_record(self, record_id: str) -> Optional[Dict]:
        """Get specific medical record"""
        try:
            response = await self.async_client.get(
                f"{self.base_url}/api/records/{record_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting record {record_id}: {str(e)}")
            return None
    
    async def get_record_section(self, record_id: str, section: str) -> Optional[Dict]:
        """Get specific section of a record
        
        Args:
            record_id: The record ID
            section: One of 'history', 'examination', 'assessment', 'plan'
        """
        try:
            response = await self.async_client.get(
                f"{self.base_url}/api/records/{record_id}/sections/{section}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting record section {section}: {str(e)}")
            return None
    
    async def get_patient_summary(self, patient_id: str) -> Dict[str, Any]:
        """Get patient summary"""
        try:
            response = await self.async_client.get(
                f"{self.base_url}/api/summary/{patient_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting patient summary: {str(e)}")
            return {}
    
    async def execute_aql_query(self, query: str) -> Optional[Dict]:
        """Execute AQL query for complex data extraction"""
        try:
            response = await self.async_client.post(
                f"{self.base_url}/ehrbase/rest/openehr/v1/query/aql",
                json={"q": query},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error executing AQL query: {str(e)}")
            return None
    
    async def create_composition(self, ehr_id: str, composition_data: Dict) -> Dict:
        """Create new clinical composition in EHRBase"""
        try:
            response = await self.async_client.post(
                f"{self.base_url}/ehrbase/rest/openehr/v1/ehr/{ehr_id}/composition",
                json=composition_data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating composition: {str(e)}")
            raise
    
    async def get_ehr_by_subject(self, subject_id: str) -> Optional[str]:
        """Get EHR ID by subject/patient ID"""
        try:
            query = f"""
            SELECT e/ehr_id/value as ehr_id
            FROM EHR e
            WHERE e/ehr_status/subject/external_ref/id/value = '{subject_id}'
            """
            result = await self.execute_aql_query(query)
            
            if result and result.get("resultSet"):
                rows = result["resultSet"]
                if rows and len(rows) > 0:
                    return rows[0].get("ehr_id")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting EHR by subject: {str(e)}")
            return None
    
    async def close(self):
        """Close the HTTP clients"""
        await self.async_client.aclose()
        self.sync_client.close()