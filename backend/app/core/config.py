from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Medical Scribe API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://medscribe:medscribe_password@localhost:5432/medical_scribe_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3100", "http://localhost:3000"]
    
    # OpenAI
    OPENAI_API_KEY: str
    WHISPER_MODEL: str = "whisper-1"
    GPT_MODEL: str = "gpt-4-turbo-preview"
    
    # EHRBase
    EHRBASE_URL: str = "http://3.223.44.85"
    EHRBASE_USERNAME: Optional[str] = None
    EHRBASE_PASSWORD: Optional[str] = None
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_FORMATS: List[str] = [".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg"]
    
    # Audio Processing
    AUDIO_CHUNK_SIZE: int = 30  # seconds
    AUDIO_SAMPLE_RATE: int = 16000
    
    # SSE
    SSE_RETRY_TIMEOUT: int = 3000  # milliseconds
    SSE_KEEPALIVE_INTERVAL: int = 15  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()