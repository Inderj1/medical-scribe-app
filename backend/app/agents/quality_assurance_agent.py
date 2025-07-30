"""Quality Assurance Agent for validating clinical notes"""
import logging
from typing import Dict, Any, List
from swarm import Agent

from app.core.config import settings
from app.agents.context_manager import handoff_context

logger = logging.getLogger(__name__)


def check_required_sections(session_id: str) -> str:
    """Check if all required sections are present"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    format_type = handoff_context.get_from_context(session_id, "format_preference", "soap")
    
    # Define required sections based on format
    if format_type == "soap":
        required_sections = ["chief_complaint", "assessment", "plan"]
    else:
        required_sections = ["chief_complaint", "assessment", "plan"]
    
    missing_sections = []
    present_sections = []
    
    for section in required_sections:
        if section in clinical_data and clinical_data[section]:
            present_sections.append(section)
        else:
            missing_sections.append(section)
    
    completeness_score = len(present_sections) / len(required_sections) if required_sections else 0
    
    handoff_context.update_context(session_id, {
        "qa_missing_sections": missing_sections,
        "qa_completeness_score": completeness_score
    })
    
    if missing_sections:
        return f"Missing required sections: {', '.join(missing_sections)}"
    else:
        return "All required sections present"


def validate_medications(session_id: str) -> str:
    """Validate medication information"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    medications = clinical_data.get("medications", [])
    
    issues = []
    validated_meds = []
    
    if isinstance(medications, list):
        for med in medications:
            if isinstance(med, dict):
                # Check for required medication fields
                if not med.get("name"):
                    issues.append("Medication missing name")
                if not med.get("dose"):
                    issues.append(f"Medication {med.get('name', 'unknown')} missing dosage")
                if not med.get("frequency"):
                    issues.append(f"Medication {med.get('name', 'unknown')} missing frequency")
                
                validated_meds.append(med)
            else:
                # Try to parse string format
                validated_meds.append({"name": str(med), "dose": "Unknown", "frequency": "Unknown"})
                issues.append(f"Medication '{med}' lacks structured information")
    
    handoff_context.update_context(session_id, {
        "qa_medication_issues": issues,
        "qa_validated_medications": validated_meds
    })
    
    if issues:
        return f"Found {len(issues)} medication documentation issues"
    else:
        return f"All {len(validated_meds)} medications properly documented"


def calculate_quality_score(session_id: str) -> str:
    """Calculate overall quality score for the clinical note"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    
    # Scoring criteria
    scores = {
        "completeness": handoff_context.get_from_context(session_id, "qa_completeness_score", 0),
        "chief_complaint_present": 1.0 if clinical_data.get("chief_complaint") else 0.0,
        "hpi_detailed": 1.0 if len(str(clinical_data.get("history_present_illness", ""))) > 50 else 0.5,
        "assessment_present": 1.0 if clinical_data.get("assessment") else 0.0,
        "plan_detailed": 1.0 if len(str(clinical_data.get("plan", ""))) > 30 else 0.5,
        "vitals_documented": 1.0 if clinical_data.get("vital_signs") else 0.7,
        "medications_structured": 1.0 if not handoff_context.get_from_context(session_id, "qa_medication_issues") else 0.5
    }
    
    # Calculate weighted average
    weights = {
        "completeness": 0.25,
        "chief_complaint_present": 0.15,
        "hpi_detailed": 0.15,
        "assessment_present": 0.15,
        "plan_detailed": 0.15,
        "vitals_documented": 0.075,
        "medications_structured": 0.075
    }
    
    total_score = sum(scores[k] * weights[k] for k in scores)
    
    handoff_context.update_context(session_id, {
        "qa_quality_score": total_score,
        "qa_detailed_scores": scores
    })
    
    return f"Quality score: {total_score:.2f}/1.0"


def generate_qa_report(session_id: str) -> str:
    """Generate comprehensive QA report"""
    qa_report = {
        "quality_score": handoff_context.get_from_context(session_id, "qa_quality_score", 0),
        "completeness_score": handoff_context.get_from_context(session_id, "qa_completeness_score", 0),
        "missing_sections": handoff_context.get_from_context(session_id, "qa_missing_sections", []),
        "medication_issues": handoff_context.get_from_context(session_id, "qa_medication_issues", []),
        "detailed_scores": handoff_context.get_from_context(session_id, "qa_detailed_scores", {}),
        "recommendations": []
    }
    
    # Add recommendations based on findings
    if qa_report["missing_sections"]:
        qa_report["recommendations"].append(
            f"Complete missing sections: {', '.join(qa_report['missing_sections'])}"
        )
    
    if qa_report["medication_issues"]:
        qa_report["recommendations"].append(
            "Review and complete medication documentation with dosages and frequencies"
        )
    
    if qa_report["quality_score"] < 0.7:
        qa_report["recommendations"].append(
            "Consider adding more detail to assessment and plan sections"
        )
    
    handoff_context.update_context(session_id, {
        "qa_report": qa_report,
        "qa_status": "completed"
    })
    
    # Store SSE update in context for later publishing
    transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
    if transcription_id:
        handoff_context.update_context(session_id, {
            "pending_sse_event": {
                "type": "qa_complete",
                "data": qa_report
            }
        })
    
    return f"QA complete. Quality score: {qa_report['quality_score']:.2f}"


def complete_processing(session_id: str) -> str:
    """Complete the entire processing pipeline"""
    try:
        # Gather all results
        final_results = {
            "transcript": handoff_context.get_from_context(session_id, "transcript"),
            "clinical_data": handoff_context.get_from_context(session_id, "clinical_data"),
            "final_note": handoff_context.get_from_context(session_id, "final_note"),
            "format_type": handoff_context.get_from_context(session_id, "format_preference"),
            "qa_report": handoff_context.get_from_context(session_id, "qa_report"),
            "medical_codes": handoff_context.get_from_context(session_id, "medical_codes", {}),
            "processing_complete": True
        }
        
        # Store final SSE update in context
        transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
        if transcription_id:
            handoff_context.update_context(session_id, {
                "pending_sse_event": {
                    "type": "completed",
                    "data": final_results
                }
            })
        
        # Update final status
        handoff_context.update_context(session_id, {
            "processing_status": "completed",
            "final_results": final_results
        })
        
        logger.info(f"Completed all processing for session {session_id}")
        
        return "Processing completed successfully. Clinical note is ready."
        
    except Exception as e:
        logger.error(f"Error completing processing: {str(e)}")
        return f"Error completing processing: {str(e)}"


# Create the quality assurance agent
quality_assurance_agent = Agent(
    name="QualityAssuranceAgent",
    instructions="""You are a clinical documentation quality assurance specialist.
    
Your responsibilities:
1. Validate clinical notes for completeness
2. Check for required sections and information
3. Validate medication documentation
4. Calculate quality scores
5. Generate QA reports with recommendations
6. Complete the processing pipeline

Available functions:
- check_required_sections(session_id) - Check for missing sections
- validate_medications(session_id) - Validate medication information
- calculate_quality_score(session_id) - Calculate overall quality
- generate_qa_report(session_id) - Generate comprehensive QA report
- complete_processing(session_id) - Finalize and send completion event

Ensure high-quality medical documentation that meets clinical standards.
""",
    functions=[
        check_required_sections,
        validate_medications,
        calculate_quality_score,
        generate_qa_report,
        complete_processing
    ]
)


# Import at the bottom
import asyncio