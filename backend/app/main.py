from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api import auth, patients, encounters, transcriptions, websocket, ehr_integration, epic_auth, ehrbase, ehrbase_local
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
    yield
    # Shutdown
    logger.info("Shutting down Medical Scribe application...")


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