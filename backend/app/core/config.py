from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Medical Scribe"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    # AI Services
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Audio Processing
    MAX_AUDIO_SIZE_MB: int = 100
    AUDIO_CHUNK_SIZE: int = 4096
    WHISPER_MODEL: str = "whisper-1"
    
    # OpenAI Realtime API Configuration
    OPENAI_REALTIME_MODEL: str = "gpt-4o-realtime-preview"
    ENABLE_INPUT_TRANSCRIPTION: bool = True
    ENABLE_FUNCTION_CALLING: bool = True
    AUDIO_SAMPLE_RATE: int = 24000
    AUDIO_CHANNELS: int = 1
    AUDIO_FORMAT: str = "pcm16"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    
    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "medical-audio"
    
    # Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # OpenEHR Configuration
    OPENEHR_API_URL: Optional[str] = None
    
    # Epic Configuration
    EPIC_CLIENT_ID: Optional[str] = None
    EPIC_CLIENT_SECRET: Optional[str] = None
    EPIC_BASE_URL: str = "https://fhir.epic.com/interconnect-fhir-oauth"
    EPIC_CLIENT_ID_PROD: str = "cb117f80-34b1-4bdf-a404-b69cf3d044de"
    EPIC_CLIENT_ID_SANDBOX: str = "0eb42959-ba12-4e23-81c9-0a523d40fd4a"
    EPIC_USE_SANDBOX: bool = True
    EPIC_REDIRECT_URI: Optional[str] = None
    EPIC_SCOPE: Optional[str] = None
    EPIC_STATE_SECRET: Optional[str] = None
    EPIC_TOKEN_ENDPOINT: Optional[str] = None
    EPIC_AUTHORIZE_ENDPOINT: Optional[str] = None
    EPIC_JWKS_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()