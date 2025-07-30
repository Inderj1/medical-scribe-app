"""Main FastAPI application with agent-based medical scribe"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1 import auth, patients, encounters, transcription, sse, ehrbase, streaming
from app.db.base_class import Base  # This imports all models
from app.db.session import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Medical Scribe API with Agent Architecture...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Initialize agent system
    from app.agents.medical_scribe_supervisor import medical_scribe_supervisor
    logger.info("Agent system initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Medical Scribe API...")
    
    # Cleanup
    from app.services.ehrbase.client import EHRBaseClient
    client = EHRBaseClient()
    await client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    description="Medical Scribe API with OpenAI Swarm Agent Architecture"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(encounters.router, prefix="/api/v1/encounters", tags=["Encounters"])
app.include_router(transcription.router, prefix="/api/v1/transcription", tags=["Transcription"])
app.include_router(streaming.router, prefix="/api/v1/streaming", tags=["Streaming"])
app.include_router(sse.router, prefix="/api/v1/sse", tags=["Server-Sent Events"])
app.include_router(ehrbase.router, prefix="/api/v1/ehrbase", tags=["EHRBase Integration"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Medical Scribe API",
        "version": settings.APP_VERSION,
        "features": [
            "Agent-based transcription processing",
            "Real-time updates via SSE",
            "EHRBase integration",
            "Clinical note generation"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check database
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        from app.db.session import get_redis
        redis = get_redis()
        redis.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy",
        "database": db_status,
        "redis": redis_status,
        "agents": "initialized",
        "version": settings.APP_VERSION
    }


@app.get("/api/test/agents")
async def test_agents():
    """Test agent system status"""
    from app.agents.context_manager import handoff_context
    from app.agents.medical_scribe_supervisor import medical_scribe_supervisor
    
    return {
        "supervisor_status": "initialized",
        "active_sessions": len(handoff_context.list_sessions()),
        "agents": [
            "TranscriptionAgent",
            "ClinicalAnalysisAgent",
            "NoteStructuringAgent",
            "QualityAssuranceAgent"
        ],
        "handoff_enabled": True
    }


@app.get("/api/test/openai")
async def test_openai():
    """Test OpenAI API connection"""
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API Connected'"}],
            max_tokens=10
        )
        
        return {
            "status": "connected",
            "model": "gpt-3.5-turbo",
            "response": response.choices[0].message.content,
            "whisper_available": True
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )