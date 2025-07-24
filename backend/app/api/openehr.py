from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from app.services.openehr_service import get_openehr_service
from app.core.auth import get_current_user
from app.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openehr", tags=["openehr"])


@router.get("/test")
async def test_openehr_connection(
    current_user: User = Depends(get_current_user)
):
    """Test the OpenEHR API connection"""
    try:
        async with await get_openehr_service() as service:
            # Try to search templates as a simple test
            templates = await service.search_templates()
            return {
                "status": "connected",
                "api_url": service.base_url,
                "templates_count": len(templates),
                "user": current_user.email
            }
    except Exception as e:
        logger.error(f"OpenEHR connection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenEHR connection failed: {str(e)}")


@router.post("/compositions")
async def create_composition(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Create a new OpenEHR composition"""
    try:
        patient_id = data.get("patient_id")
        encounter_id = data.get("encounter_id")
        clinical_notes = data.get("clinical_notes", {})
        vitals = data.get("vitals")
        
        if not patient_id or not encounter_id:
            raise HTTPException(status_code=400, detail="patient_id and encounter_id are required")
        
        async with await get_openehr_service() as service:
            result = await service.create_composition(
                patient_id=patient_id,
                encounter_id=encounter_id,
                clinical_notes=clinical_notes,
                vitals=vitals
            )
            
            if "error" in result:
                raise HTTPException(status_code=500, detail=result["error"])
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating composition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compositions/{patient_id}")
async def get_patient_compositions(
    patient_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get patient's compositions from OpenEHR"""
    try:
        async with await get_openehr_service() as service:
            compositions = await service.get_patient_compositions(patient_id, limit)
            return {
                "patient_id": patient_id,
                "compositions": compositions,
                "count": len(compositions)
            }
    except Exception as e:
        logger.error(f"Error getting compositions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def search_templates(
    query: str = "",
    current_user: User = Depends(get_current_user)
):
    """Search available OpenEHR templates"""
    try:
        async with await get_openehr_service() as service:
            templates = await service.search_templates(query)
            return {
                "templates": templates,
                "count": len(templates),
                "query": query
            }
    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))