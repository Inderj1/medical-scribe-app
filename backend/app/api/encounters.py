from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from app.db.session import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.services.openehr_service import get_openehr_service

router = APIRouter()


class TodoItem(BaseModel):
    id: str
    text: str
    completed: bool = False
    category: str  # 'medication', 'followup', 'lifestyle', 'monitoring'
    priority: str  # 'high', 'medium', 'low'


class VisitSummaryRequest(BaseModel):
    clinical_data: Dict[str, Any]
    patient_info: Optional[Dict[str, Any]] = None
    encounter_info: Optional[Dict[str, Any]] = None


class VisitSummaryResponse(BaseModel):
    id: str
    visit_date: str
    provider: str
    reason_for_visit: str
    key_findings: List[str]
    todo_items: List[TodoItem]
    follow_up_instructions: str
    next_appointment: Optional[str] = None
    one_liner_summary: str
    patient_friendly_diagnosis: List[str]
    emergency_instructions: List[str]


@router.get("/")
async def get_encounters(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of encounters"""
    try:
        openehr_service = await get_openehr_service()
        patients = await openehr_service.get_patients()
        return {"encounters": patients}
    except Exception as e:
        return {"encounters": [], "error": str(e)}


@router.get("/patients")
async def get_patients(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get patients from EHR system"""
    try:
        openehr_service = await get_openehr_service()
        patients = await openehr_service.get_patients()
        return {"patients": patients}
    except Exception as e:
        return {"patients": [], "error": str(e)}


@router.get("/dotphrases")
async def get_dotphrases(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dotphrases from EHR system"""
    try:
        openehr_service = await get_openehr_service()
        dotphrases = await openehr_service.get_dotphrases()
        return {"dotphrases": dotphrases}
    except Exception as e:
        return {"dotphrases": [], "error": str(e)}


@router.get("/{encounter_id}")
async def get_encounter(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get encounter by ID"""
    # Implementation placeholder
    return {"id": encounter_id}


@router.post("/{encounter_id}/generate-summary")
async def generate_after_visit_summary(
    encounter_id: str,
    request: VisitSummaryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> VisitSummaryResponse:
    """Generate after-visit summary for patient"""
    try:
        # Extract clinical data
        clinical_data = request.clinical_data
        patient_info = request.patient_info or {}
        encounter_info = request.encounter_info or {}
        
        # Generate patient-friendly summary using AI
        summary = await _generate_patient_summary(
            clinical_data, 
            patient_info, 
            encounter_info,
            encounter_id
        )
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@router.get("/{encounter_id}/summary")
async def get_after_visit_summary(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> VisitSummaryResponse:
    """Get existing after-visit summary"""
    # Implementation placeholder - would fetch from database
    # For now, return a sample response
    return VisitSummaryResponse(
        id=f"summary-{encounter_id}",
        visit_date=datetime.now().isoformat(),
        provider="Dr. Smith",
        reason_for_visit="Follow-up consultation",
        key_findings=["You came in for a follow-up visit", "Your vital signs were checked"],
        todo_items=[
            TodoItem(
                id="1",
                text="Take your medications as prescribed",
                category="medication",
                priority="high"
            )
        ],
        follow_up_instructions="Please schedule a follow-up appointment in 2 weeks",
        one_liner_summary="Follow-up visit completed with medication review",
        patient_friendly_diagnosis=["Overall health is improving"],
        emergency_instructions=["Call 911 if you experience severe symptoms"]
    )


@router.put("/{encounter_id}/summary")
async def update_after_visit_summary(
    encounter_id: str,
    summary: VisitSummaryResponse,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> VisitSummaryResponse:
    """Update after-visit summary"""
    # Implementation placeholder - would save to database
    return summary


async def _generate_patient_summary(
    clinical_data: Dict[str, Any],
    patient_info: Dict[str, Any],
    encounter_info: Dict[str, Any],
    encounter_id: str
) -> VisitSummaryResponse:
    """Generate patient-friendly summary using AI"""
    
    # Medical to layman translation dictionary
    medical_translations = {
        'dyspnea': 'difficulty breathing',
        'hemoptysis': 'coughing up blood',
        'thoracentesis': 'fluid removal from lung area',
        'bronchogenic carcinoma': 'lung cancer',
        'pleural effusion': 'fluid around the lungs',
        'hypertension': 'high blood pressure',
        'diabetes': 'high blood sugar',
        'tachycardia': 'fast heart rate',
        'bradycardia': 'slow heart rate'
    }
    
    def translate_to_layman(text: str) -> str:
        """Convert medical terms to patient-friendly language"""
        if not text:
            return text
            
        translated = text.lower()
        for medical, layman in medical_translations.items():
            translated = translated.replace(medical, layman)
        return translated.capitalize()
    
    # Extract key information
    chief_complaint = clinical_data.get('chief_complaint', 'health concerns')
    diagnoses = clinical_data.get('diagnoses', [])
    plan_items = clinical_data.get('planItems', [])
    vitals = clinical_data.get('vitals', {})
    
    # Generate key findings
    key_findings = []
    key_findings.append(f"You came in because of {translate_to_layman(chief_complaint)}")
    
    if vitals:
        bp = vitals.get('blood_pressure')
        if bp:
            key_findings.append(f"Your blood pressure was {bp}")
        hr = vitals.get('heart_rate')
        if hr:
            key_findings.append(f"Your heart rate was {hr} beats per minute")
    
    key_findings.append("We discussed your symptoms and medical history")
    key_findings.append("Tests and examinations were performed to understand your condition better")
    
    # Generate TODO items from plan
    todo_items = []
    todo_counter = 1
    
    for item in plan_items:
        category = item.get('category', 'action')
        text = item.get('text', '')
        
        if category == 'medication':
            todo_items.append(TodoItem(
                id=str(todo_counter),
                text=translate_to_layman(text),
                category='medication',
                priority='high'
            ))
        elif category == 'education':
            todo_items.append(TodoItem(
                id=str(todo_counter),
                text=translate_to_layman(text),
                category='lifestyle',
                priority='medium'
            ))
        elif category == 'followup':
            todo_items.append(TodoItem(
                id=str(todo_counter),
                text='Schedule follow-up appointment as discussed',
                category='followup',
                priority='high'
            ))
        
        todo_counter += 1
    
    # Add default todos
    default_todos = [
        TodoItem(
            id=str(todo_counter),
            text="Take all medications as prescribed",
            category="medication",
            priority="high"
        ),
        TodoItem(
            id=str(todo_counter + 1),
            text="Follow up with your doctor as scheduled",
            category="followup",
            priority="high"
        ),
        TodoItem(
            id=str(todo_counter + 2),
            text="Contact us if your symptoms get worse",
            category="monitoring",
            priority="high"
        )
    ]
    
    todo_items.extend(default_todos)
    
    # Generate patient-friendly diagnoses
    patient_friendly_diagnosis = []
    for diagnosis in diagnoses:
        if isinstance(diagnosis, dict):
            primary = diagnosis.get('primary', '')
            patient_friendly_diagnosis.append(translate_to_layman(primary))
        else:
            patient_friendly_diagnosis.append(translate_to_layman(str(diagnosis)))
    
    # Generate emergency instructions
    emergency_instructions = [
        "Call 911 or go to the emergency room if you have severe difficulty breathing",
        "Contact our office immediately if you cough up blood",
        "Seek immediate care if you have severe chest pain",
        "Call us if you develop fever over 101°F (38.3°C)"
    ]
    
    # Calculate next appointment date (2 weeks from now)
    from datetime import timedelta
    next_appointment = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    return VisitSummaryResponse(
        id=f"summary-{encounter_id}",
        visit_date=encounter_info.get('encounter_date', datetime.now().isoformat()),
        provider=encounter_info.get('provider_name', 'Dr. Smith'),
        reason_for_visit=translate_to_layman(chief_complaint),
        key_findings=key_findings,
        todo_items=todo_items,
        follow_up_instructions="Please schedule a follow-up appointment in 1-2 weeks to review your progress and any test results. If you experience worsening symptoms or new concerns before then, please contact our office immediately.",
        next_appointment=next_appointment,
        one_liner_summary=f"{datetime.now().strftime('%Y-%m-%d')}: Visit for {translate_to_layman(chief_complaint)} - tests ordered, treatment plan discussed",
        patient_friendly_diagnosis=patient_friendly_diagnosis,
        emergency_instructions=emergency_instructions
    )