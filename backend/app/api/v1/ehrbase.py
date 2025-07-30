"""EHRBase integration API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
import logging

from app.core.security import get_current_active_user
from app.models.user import User
from app.services.ehrbase.client import EHRBaseClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def check_ehrbase_health(
    current_user: User = Depends(get_current_active_user)
):
    """Check EHRBase connectivity"""
    client = EHRBaseClient()
    try:
        # Try to execute a simple query
        result = await client.execute_aql_query("SELECT e/ehr_id/value FROM EHR e LIMIT 1")
        return {
            "status": "connected",
            "url": client.base_url,
            "test_query": "success" if result else "failed"
        }
    except Exception as e:
        logger.error(f"EHRBase health check failed: {e}")
        return {
            "status": "error",
            "url": client.base_url,
            "error": str(e)
        }
    finally:
        await client.close()


@router.get("/patients/search")
async def search_ehr_patients(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    mrn: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Search patients in EHRBase"""
    client = EHRBaseClient()
    try:
        filters = {}
        if first_name:
            filters["firstName"] = first_name
        if last_name:
            filters["lastName"] = last_name
        if mrn:
            filters["mrn"] = mrn
            
        patients = await client.search_patients(filters)
        return {"patients": patients, "count": len(patients)}
    except Exception as e:
        logger.error(f"EHRBase patient search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/patients/{patient_id}/summary")
async def get_patient_summary(
    patient_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get patient summary from EHRBase"""
    client = EHRBaseClient()
    try:
        summary = await client.get_patient_summary(patient_id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get patient summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/patients/{patient_id}/records")
async def get_patient_records(
    patient_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get patient records from EHRBase"""
    client = EHRBaseClient()
    try:
        records = await client.get_patient_records(patient_id)
        return {"records": records, "count": len(records)}
    except Exception as e:
        logger.error(f"Failed to get patient records: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/records/{record_id}")
async def get_record(
    record_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific record from EHRBase"""
    client = EHRBaseClient()
    try:
        record = await client.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get record: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/records/{record_id}/sections/{section}")
async def get_record_section(
    record_id: str,
    section: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific section of a record"""
    if section not in ["history", "examination", "assessment", "plan"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid section. Must be one of: history, examination, assessment, plan"
        )
    
    client = EHRBaseClient()
    try:
        section_data = await client.get_record_section(record_id, section)
        if not section_data:
            raise HTTPException(status_code=404, detail="Section not found")
        return section_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get record section: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/query/aql")
async def execute_aql_query(
    query_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Execute AQL query on EHRBase"""
    if "query" not in query_data:
        raise HTTPException(status_code=400, detail="Query is required")
    
    client = EHRBaseClient()
    try:
        result = await client.execute_aql_query(query_data["query"])
        return result
    except Exception as e:
        logger.error(f"AQL query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()