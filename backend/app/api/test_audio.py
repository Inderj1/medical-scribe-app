from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["test"])

class AudioTest(BaseModel):
    audio_chunk: str

@router.post("/audio")
async def test_audio(data: AudioTest):
    """Test audio chunk reception"""
    try:
        # Decode base64
        audio_bytes = base64.b64decode(data.audio_chunk)
        logger.info(f"Received audio chunk of {len(audio_bytes)} bytes")
        
        return {
            "status": "success",
            "bytes_received": len(audio_bytes),
            "first_10_bytes": list(audio_bytes[:10])
        }
    except Exception as e:
        logger.error(f"Error processing test audio: {e}")
        raise HTTPException(status_code=400, detail=str(e))