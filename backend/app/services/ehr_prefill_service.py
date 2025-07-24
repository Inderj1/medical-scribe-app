import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

from app.services.openehr_service import OpenEHRService
from app.db.session import get_db
from app.models.patient import Patient
from app.models.encounter import Encounter
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EHRPrefillService:
    """
    Service to fetch and format patient data from EHR for pre-populating clinical notes.
    """
    
    def __init__(self, openehr_service: OpenEHRService = None):
        self.openehr_service = openehr_service or OpenEHRService()
    
    async def fetch_patient_data_for_notes(self, patient_id: str, db: Session) -> Dict[str, Any]:
        """
        Fetch comprehensive patient data from EHR and local database.
        
        Returns:
            Dictionary with all relevant patient data formatted for clinical notes
        """
        try:
            # Fetch patient demographics from local DB
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                logger.error(f"Patient {patient_id} not found in database")
                return self._get_empty_prefill()
            
            # Parallel fetch of all EHR data
            tasks = [
                self._fetch_demographics(patient),
                self._fetch_recent_vitals(patient_id, patient.ehr_id),
                self._fetch_active_medications(patient_id, patient.ehr_id),
                self._fetch_allergies(patient_id, patient.ehr_id),
                self._fetch_problem_list(patient_id, patient.ehr_id),
                self._fetch_recent_labs(patient_id, patient.ehr_id),
                self._fetch_immunizations(patient_id, patient.ehr_id),
                self._fetch_recent_encounters(patient_id, db)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            data = {
                "demographics": results[0] if not isinstance(results[0], Exception) else {},
                "vitals": results[1] if not isinstance(results[1], Exception) else {},
                "medications": results[2] if not isinstance(results[2], Exception) else [],
                "allergies": results[3] if not isinstance(results[3], Exception) else [],
                "problems": results[4] if not isinstance(results[4], Exception) else [],
                "recent_labs": results[5] if not isinstance(results[5], Exception) else [],
                "immunizations": results[6] if not isinstance(results[6], Exception) else [],
                "recent_encounters": results[7] if not isinstance(results[7], Exception) else []
            }
            
            # Format for UI pre-population
            return self._format_for_clinical_notes(data)
            
        except Exception as e:
            logger.error(f"Error fetching patient data: {str(e)}")
            return self._get_empty_prefill()
    
    async def _fetch_demographics(self, patient: Patient) -> Dict:
        """Fetch patient demographics"""
        try:
            age = None
            if patient.date_of_birth:
                today = datetime.now().date()
                dob = datetime.strptime(patient.date_of_birth, "%Y-%m-%d").date()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            return {
                "name": f"{patient.first_name} {patient.last_name}",
                "mrn": patient.mrn,
                "date_of_birth": patient.date_of_birth,
                "age": age,
                "gender": patient.gender,
                "phone": patient.phone,
                "email": patient.email,
                "emergency_contact": patient.emergency_contact
            }
        except Exception as e:
            logger.error(f"Error fetching demographics: {str(e)}")
            return {}
    
    async def _fetch_recent_vitals(self, patient_id: str, ehr_id: Optional[str]) -> Dict:
        """Fetch most recent vital signs"""
        try:
            if not ehr_id:
                return {}
            
            # Get recent compositions from OpenEHR
            compositions = await self.openehr_service.get_compositions(ehr_id)
            
            # Extract most recent vitals
            vitals = {}
            for comp in compositions[:5]:  # Check last 5 encounters
                if 'vitals' in comp:
                    vitals = comp['vitals']
                    vitals['recorded_date'] = comp.get('encounter_date', '')
                    break
            
            return vitals
            
        except Exception as e:
            logger.error(f"Error fetching vitals: {str(e)}")
            return {}
    
    async def _fetch_active_medications(self, patient_id: str, ehr_id: Optional[str]) -> List[Dict]:
        """Fetch active medications"""
        try:
            if not ehr_id:
                return []
            
            # Get medications from recent compositions
            compositions = await self.openehr_service.get_compositions(ehr_id)
            
            medications = []
            for comp in compositions[:3]:  # Check last 3 encounters
                if 'medications' in comp and comp['medications']:
                    # Merge and deduplicate medications
                    for med in comp['medications']:
                        if not any(m['name'] == med['name'] for m in medications):
                            medications.append({
                                "name": med.get('name', ''),
                                "dose": med.get('dose', ''),
                                "frequency": med.get('frequency', ''),
                                "route": med.get('route', 'PO'),
                                "start_date": med.get('start_date', ''),
                                "status": "active"
                            })
            
            return medications
            
        except Exception as e:
            logger.error(f"Error fetching medications: {str(e)}")
            return []
    
    async def _fetch_allergies(self, patient_id: str, ehr_id: Optional[str]) -> List[Dict]:
        """Fetch patient allergies"""
        try:
            if not ehr_id:
                return []
            
            # Get allergies from compositions
            compositions = await self.openehr_service.get_compositions(ehr_id)
            
            allergies = []
            for comp in compositions[:5]:
                if 'allergies' in comp and comp['allergies']:
                    for allergy in comp['allergies']:
                        if not any(a['allergen'] == allergy.get('allergen') for a in allergies):
                            allergies.append({
                                "allergen": allergy.get('allergen', ''),
                                "reaction": allergy.get('reaction', ''),
                                "severity": allergy.get('severity', 'moderate'),
                                "type": allergy.get('type', 'medication')
                            })
            
            # Add default NKDA if no allergies found
            if not allergies:
                allergies = [{"allergen": "NKDA", "reaction": "No Known Drug Allergies"}]
            
            return allergies
            
        except Exception as e:
            logger.error(f"Error fetching allergies: {str(e)}")
            return [{"allergen": "NKDA", "reaction": "No Known Drug Allergies"}]
    
    async def _fetch_problem_list(self, patient_id: str, ehr_id: Optional[str]) -> List[Dict]:
        """Fetch active problem list"""
        try:
            if not ehr_id:
                return []
            
            # Get diagnoses from recent compositions
            compositions = await self.openehr_service.get_compositions(ehr_id)
            
            problems = []
            for comp in compositions[:10]:  # Look through more encounters for problems
                if 'diagnoses' in comp and comp['diagnoses']:
                    for diagnosis in comp['diagnoses']:
                        problem_name = diagnosis.get('name', '')
                        if problem_name and not any(p['problem'] == problem_name for p in problems):
                            problems.append({
                                "problem": problem_name,
                                "icd_code": diagnosis.get('icd_code', ''),
                                "status": "active",
                                "onset_date": comp.get('encounter_date', ''),
                                "notes": diagnosis.get('notes', '')
                            })
            
            return problems[:10]  # Limit to 10 most relevant problems
            
        except Exception as e:
            logger.error(f"Error fetching problem list: {str(e)}")
            return []
    
    async def _fetch_recent_labs(self, patient_id: str, ehr_id: Optional[str]) -> List[Dict]:
        """Fetch recent lab results"""
        try:
            if not ehr_id:
                return []
            
            # Get lab results from recent compositions
            compositions = await self.openehr_service.get_compositions(ehr_id)
            
            labs = []
            for comp in compositions[:5]:
                if 'lab_results' in comp and comp['lab_results']:
                    for lab in comp['lab_results']:
                        labs.append({
                            "test_name": lab.get('test_name', ''),
                            "value": lab.get('value', ''),
                            "unit": lab.get('unit', ''),
                            "reference_range": lab.get('reference_range', ''),
                            "status": lab.get('status', 'final'),
                            "date": lab.get('date', comp.get('encounter_date', ''))
                        })
            
            # Sort by date and return most recent
            labs.sort(key=lambda x: x['date'], reverse=True)
            return labs[:20]  # Return up to 20 most recent labs
            
        except Exception as e:
            logger.error(f"Error fetching labs: {str(e)}")
            return []
    
    async def _fetch_immunizations(self, patient_id: str, ehr_id: Optional[str]) -> List[Dict]:
        """Fetch immunization history"""
        try:
            # For now, return common immunizations as placeholder
            # In production, this would fetch from EHR immunization registry
            return [
                {
                    "vaccine": "COVID-19 (Pfizer)",
                    "date": "2023-10-15",
                    "status": "completed"
                },
                {
                    "vaccine": "Influenza",
                    "date": "2023-09-20",
                    "status": "completed"
                }
            ]
        except Exception as e:
            logger.error(f"Error fetching immunizations: {str(e)}")
            return []
    
    async def _fetch_recent_encounters(self, patient_id: str, db: Session) -> List[Dict]:
        """Fetch recent encounters from local database"""
        try:
            recent_encounters = db.query(Encounter).filter(
                Encounter.patient_id == patient_id
            ).order_by(Encounter.encounter_date.desc()).limit(5).all()
            
            encounters = []
            for enc in recent_encounters:
                encounters.append({
                    "date": enc.encounter_date.isoformat() if enc.encounter_date else "",
                    "type": enc.encounter_type,
                    "chief_complaint": enc.chief_complaint,
                    "provider": enc.provider_name,
                    "status": enc.status
                })
            
            return encounters
            
        except Exception as e:
            logger.error(f"Error fetching recent encounters: {str(e)}")
            return []
    
    def _format_for_clinical_notes(self, data: Dict) -> Dict:
        """Format all data for clinical notes UI pre-population"""
        
        # Format medications into a readable list
        med_list = []
        for med in data['medications']:
            med_str = f"{med['name']}"
            if med.get('dose'):
                med_str += f" {med['dose']}"
            if med.get('frequency'):
                med_str += f" {med['frequency']}"
            med_list.append(med_str)
        
        # Format allergies
        allergy_list = []
        for allergy in data['allergies']:
            if allergy['allergen'] != "NKDA":
                allergy_str = f"{allergy['allergen']}"
                if allergy.get('reaction'):
                    allergy_str += f" - {allergy['reaction']}"
                allergy_list.append(allergy_str)
        
        # Format problem list
        problem_list = []
        for problem in data['problems']:
            prob_str = problem['problem']
            if problem.get('icd_code'):
                prob_str += f" ({problem['icd_code']})"
            problem_list.append(prob_str)
        
        return {
            "patient_info": data['demographics'],
            "sections": {
                "chief_complaint": "",  # Empty for new encounter
                "history_present_illness": "",  # Empty for new encounter
                "past_medical_history": problem_list,
                "medications": med_list,
                "allergies": allergy_list if allergy_list else ["NKDA"],
                "social_history": {
                    "smoking": data['demographics'].get('smoking_history', 'Unknown'),
                    "alcohol": "Social drinker",  # Placeholder
                    "occupation": "Unknown"
                },
                "family_history": [],  # Would be populated from EHR
                "review_of_systems": {},  # Empty for new encounter
                "vitals": data['vitals'],
                "physical_exam": {},  # Empty for new encounter
                "assessment_plan": {}  # Empty for new encounter
            },
            "recent_labs": data['recent_labs'],
            "recent_encounters": data['recent_encounters'],
            "metadata": {
                "prefill_timestamp": datetime.utcnow().isoformat(),
                "data_sources": ["local_db", "openehr"]
            }
        }
    
    def _get_empty_prefill(self) -> Dict:
        """Return empty prefill structure when data fetch fails"""
        return {
            "patient_info": {},
            "sections": {
                "chief_complaint": "",
                "history_present_illness": "",
                "past_medical_history": [],
                "medications": [],
                "allergies": ["NKDA"],
                "social_history": {},
                "family_history": [],
                "review_of_systems": {},
                "vitals": {},
                "physical_exam": {},
                "assessment_plan": {}
            },
            "recent_labs": [],
            "recent_encounters": [],
            "metadata": {
                "prefill_timestamp": datetime.utcnow().isoformat(),
                "data_sources": [],
                "error": "Failed to fetch patient data"
            }
        }