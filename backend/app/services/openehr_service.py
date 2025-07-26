import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OpenEHRService:
    """Service for integrating with OpenEHR API"""
    
    def __init__(self):
        self.base_url = settings.OPENEHR_API_URL or 'http://98.86.40.56'
        self.ehr_direct_url = 'http://98.86.40.56'
        
        # Always create client for EHR integration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30.0
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def create_composition(
        self,
        patient_id: str,
        encounter_id: str,
        clinical_notes: Dict[str, Any],
        vitals: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an OpenEHR composition from clinical notes
        """
        try:
            # Prepare the composition data
            composition_data = {
                "archetype_id": "openEHR-EHR-COMPOSITION.encounter.v1",
                "language": "en",
                "territory": "US",
                "context": {
                    "start_time": datetime.utcnow().isoformat(),
                    "setting": "primary_care",
                    "health_care_facility": {
                        "name": "Medical Scribe Clinic"
                    }
                },
                "content": []
            }
            
            # Add clinical notes sections
            for section, content in clinical_notes.items():
                if content and isinstance(content, dict) and content.get('text'):
                    section_data = {
                        "archetype_id": f"openEHR-EHR-EVALUATION.clinical_synopsis.v1",
                        "name": section.replace('_', ' ').title(),
                        "data": {
                            "synopsis": content['text']
                        }
                    }
                    composition_data["content"].append(section_data)
            
            # Add vitals if provided
            if vitals:
                vitals_data = {
                    "archetype_id": "openEHR-EHR-OBSERVATION.vital_signs.v1",
                    "name": "Vital Signs",
                    "data": vitals
                }
                composition_data["content"].append(vitals_data)
            
            # Send to OpenEHR API
            response = await self.client.post(
                f"/ehr/{patient_id}/compositions",
                json=composition_data,
                params={"encounter_id": encounter_id}
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to create OpenEHR composition: {response.status_code} - {response.text}")
                return {"error": f"Failed to create composition: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error creating OpenEHR composition: {str(e)}")
            return {"error": str(e)}
    
    async def get_patient_compositions(
        self,
        patient_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve patient's compositions from OpenEHR
        """
        try:
            response = await self.client.get(
                f"/ehr/{patient_id}/compositions",
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get compositions: {response.status_code}")
                return self._get_mock_compositions()
                
        except Exception as e:
            logger.error(f"Error getting compositions: {str(e)}")
            return self._get_mock_compositions()

    async def get_patients(self, **filters) -> List[Dict[str, Any]]:
        """
        Get patients from EHR system
        """
        try:
            direct_client = httpx.AsyncClient(base_url=self.ehr_direct_url, timeout=30.0)
            response = await direct_client.get("/api/patients", params=filters)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get patients: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting patients: {str(e)}")
            return []
        finally:
            await direct_client.aclose()

    async def get_dotphrases(self) -> List[Dict[str, Any]]:
        """
        Get dotphrases from EHR system
        """
        try:
            direct_client = httpx.AsyncClient(base_url=self.ehr_direct_url, timeout=30.0)
            response = await direct_client.get("/api/dotphrases")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get dotphrases: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting dotphrases: {str(e)}")
            return []
        finally:
            await direct_client.aclose()
    
    async def update_composition(
        self,
        patient_id: str,
        composition_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing OpenEHR composition
        """
        try:
            response = await self.client.put(
                f"/ehr/{patient_id}/compositions/{composition_id}",
                json=updates
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to update composition: {response.status_code}")
                return {"error": f"Failed to update: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error updating composition: {str(e)}")
            return {"error": str(e)}
    
    async def get_compositions(self, ehr_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Alias for get_patient_compositions for backward compatibility
        """
        return await self.get_patient_compositions(ehr_id, limit)
    
    async def search_templates(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Search available OpenEHR templates
        """
        try:
            response = await self.client.get(
                "/templates",
                params={"q": query} if query else {}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to search templates: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching templates: {str(e)}")
            return []
    
    async def validate_composition(
        self,
        composition_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a composition against OpenEHR archetypes
        """
        try:
            response = await self.client.post(
                "/validate/composition",
                json=composition_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"valid": False, "errors": [response.text]}
                
        except Exception as e:
            logger.error(f"Error validating composition: {str(e)}")
            return {"valid": False, "errors": [str(e)]}
    
    def _get_mock_compositions(self) -> List[Dict[str, Any]]:
        """Return mock composition data when OpenEHR is not available"""
        return [
            {
                "encounter_date": "2024-01-15T10:30:00",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": "72",
                    "temperature": "98.6°F",
                    "oxygen_saturation": "98%"
                },
                "medications": [
                    {
                        "name": "Lisinopril",
                        "dose": "10mg",
                        "frequency": "daily",
                        "route": "PO"
                    },
                    {
                        "name": "Metformin",
                        "dose": "500mg",
                        "frequency": "twice daily",
                        "route": "PO"
                    }
                ],
                "allergies": [
                    {
                        "allergen": "Penicillin",
                        "reaction": "Rash",
                        "severity": "moderate"
                    }
                ],
                "diagnoses": [
                    {
                        "name": "Hypertension",
                        "icd_code": "I10",
                        "notes": "Well controlled"
                    },
                    {
                        "name": "Type 2 Diabetes",
                        "icd_code": "E11.9",
                        "notes": "Diet controlled"
                    }
                ],
                "lab_results": [
                    {
                        "test_name": "HbA1c",
                        "value": "6.8",
                        "unit": "%",
                        "reference_range": "<7.0",
                        "status": "final",
                        "date": "2024-01-10"
                    }
                ]
            }
        ]


# Singleton instance
openehr_service = None


async def get_openehr_service() -> OpenEHRService:
    """Get or create OpenEHR service instance"""
    global openehr_service
    if openehr_service is None:
        openehr_service = OpenEHRService()
    return openehr_service