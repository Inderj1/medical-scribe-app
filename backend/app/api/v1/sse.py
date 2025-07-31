"""Server-Sent Events API endpoints"""
from fastapi import APIRouter, Depends, Request, Query
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import logging
from datetime import datetime

from app.core.security import get_current_active_user, decode_token
from app.core.sse_manager import sse_manager
from app.models.user import User
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: Session):
    """Get user from token query parameter (for SSE which doesn't support headers)"""
    # Development bypass when DEBUG is True
    from app.core.config import settings
    if settings.DEBUG:
        logger.info(f"DEBUG: SSE Authentication bypass active. Token received: {token[:20] if token else 'None'}...")
        # Create or get a test user for development
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                first_name="Test",
                last_name="User", 
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        return test_user
    
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user and user.is_active:
                return user
    except Exception as e:
        logger.error(f"Token validation error: {e}")
    return None


@router.get("/transcription/{transcription_id}")
async def transcription_events(
    request: Request,
    transcription_id: str,
    token: str = Query(..., description="JWT token"),
    db: Session = Depends(get_db)
):
    """SSE endpoint for real-time transcription updates"""
    
    # Validate user from token
    user = await get_user_from_token(token, db)
    if not user:
        # Return error event and close
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({"error": "Unauthorized"})
            }
        return EventSourceResponse(error_generator())
    
    async def event_generator():
        """Generate SSE events for transcription updates"""
        try:
            logger.info(f"SSE connection opened for transcription {transcription_id} by user {user.email}")
            
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "message": "Connected to transcription updates",
                    "transcription_id": transcription_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            # Subscribe to transcription channel
            channel = f"transcription:{transcription_id}"
            async for event in sse_manager.subscribe(channel):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE for transcription {transcription_id}")
                    break
                
                # Send event to client
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"]),
                    "id": event.get("timestamp", ""),
                    "retry": 3000  # Retry after 3 seconds if connection lost
                }
                
                # Log significant events
                if event["type"] in ["completed", "error"]:
                    logger.info(f"Transcription {transcription_id} {event['type']}")
                    break
            
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for transcription {transcription_id}")
        except Exception as e:
            logger.error(f"SSE error for transcription {transcription_id}: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
        finally:
            logger.info(f"SSE connection closed for transcription {transcription_id}")
    
    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.get("/health")
async def sse_health_check():
    """Health check endpoint for SSE"""
    
    async def health_generator():
        yield {
            "event": "health",
            "data": json.dumps({
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "SSE service is healthy"
            })
        }
    
    return EventSourceResponse(health_generator())


@router.get("/test")
async def sse_test(
    token: str = Query(..., description="JWT token"),
    db: Session = Depends(get_db)
):
    """Test SSE endpoint that sends periodic updates"""
    
    # Validate user
    user = await get_user_from_token(token, db)
    if not user:
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({"error": "Unauthorized"})
            }
        return EventSourceResponse(error_generator())
    
    async def test_generator():
        """Generate test events every 2 seconds"""
        try:
            for i in range(10):
                yield {
                    "event": "test",
                    "data": json.dumps({
                        "message": f"Test event {i + 1}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "user": user.email
                    })
                }
                await asyncio.sleep(2)
            
            yield {
                "event": "complete",
                "data": json.dumps({
                    "message": "Test completed",
                    "total_events": 10
                })
            }
            
        except asyncio.CancelledError:
            pass
    
    return EventSourceResponse(test_generator())