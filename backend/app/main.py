from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api import auth, patients, encounters, transcriptions, websocket, ehr_integration, epic_auth, ehrbase, ehrbase_local, openehr, enhanced_websocket, agent_websocket, batch_transcription, streaming_transcription, swarm_api
from app.db.session import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Medical Scribe application...")
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize the medical scribe supervisors
    from app.agents.batch_medical_scribe_supervisor import get_medical_scribe_supervisor
    from app.agents.streaming_medical_scribe_supervisor import get_streaming_supervisor
    from app.agents.swarm_supervisor import get_swarm_supervisor
    
    batch_supervisor = get_medical_scribe_supervisor()
    streaming_supervisor = get_streaming_supervisor()
    swarm_supervisor = get_swarm_supervisor()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Medical Scribe application...")
    
    # Shutdown supervisors
    await batch_supervisor.shutdown()
    await streaming_supervisor.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(encounters.router, prefix="/api/encounters", tags=["encounters"])
app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["transcriptions"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(ehr_integration.router, prefix="/api/ehr", tags=["ehr"])
app.include_router(epic_auth.router, prefix="/api/auth", tags=["epic-auth"])
app.include_router(ehrbase.router, prefix="/api/ehrbase/proxy", tags=["ehrbase"])
app.include_router(ehrbase_local.router, prefix="/api/ehrbase-local", tags=["ehrbase-local"])
app.include_router(openehr.router, prefix="/api", tags=["openehr"])
app.include_router(enhanced_websocket.router, prefix="/api/v1/ws", tags=["enhanced-websocket"])
app.include_router(agent_websocket.router, prefix="/api/v2", tags=["agent-websocket"])
app.include_router(batch_transcription.router, prefix="/api/v1/transcription", tags=["batch-transcription"])
app.include_router(streaming_transcription.router, prefix="/api/v1/streaming", tags=["streaming-transcription"])
app.include_router(swarm_api.router, prefix="/api/v2/swarm", tags=["swarm-agents"])


@app.get("/")
async def root():
    return {
        "message": "Medical Scribe API",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }


@app.get("/api/test/openai")
async def test_openai():
    """Test OpenAI API connection"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Try a simple completion to test the API key
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API key is valid'"}],
            max_tokens=10
        )
        
        return {
            "status": "success",
            "message": "OpenAI API key is valid",
            "response": response.choices[0].message.content
        }
    except Exception as e:
        logger.error(f"OpenAI API test failed: {type(e).__name__}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }