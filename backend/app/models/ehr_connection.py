from sqlalchemy import Column, String, DateTime, Boolean, Enum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from cryptography.fernet import Fernet
import uuid
import enum
import os

from app.db.session import Base
from app.core.config import settings


class EHRSystem(str, enum.Enum):
    EPIC = "epic"
    CERNER = "cerner"
    ALLSCRIPTS = "allscripts"
    ATHENAHEALTH = "athenahealth"
    NEXTGEN = "nextgen"
    ECLINICALWORKS = "eclinicalworks"
    PRACTICEFUSION = "practicefusion"
    CUSTOM = "custom"


class EHRConnection(Base):
    __tablename__ = "ehr_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String(100), nullable=False, index=True)
    organization_name = Column(String(255), nullable=False)
    
    # EHR System Details
    ehr_system = Column(Enum(EHRSystem), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_version = Column(String(20), default="R4")  # FHIR version
    
    # Authentication
    client_id = Column(String(255), nullable=False)
    encrypted_client_secret = Column(Text, nullable=False)  # Encrypted
    tenant_id = Column(String(255))  # For multi-tenant systems
    private_key = Column(Text)  # For JWT authentication (Epic)
    
    # Connection Settings
    is_active = Column(Boolean, default=True)
    is_sandbox = Column(Boolean, default=False)
    
    # Rate Limiting
    rate_limit_per_minute = Column(Integer, default=100)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_tested_at = Column(DateTime(timezone=True))
    last_sync_at = Column(DateTime(timezone=True))
    
    # Configuration
    custom_config = Column(Text)  # JSON for EHR-specific settings
    
    @property
    def _encryption_key(self):
        """Get or create encryption key"""
        key = os.environ.get('EHR_ENCRYPTION_KEY')
        if not key:
            # Generate a key if not set (should be set in production)
            key = Fernet.generate_key().decode()
            os.environ['EHR_ENCRYPTION_KEY'] = key
        return key.encode()
        
    def encrypt_secret(self, secret: str) -> None:
        """Encrypt and store client secret"""
        f = Fernet(self._encryption_key)
        self.encrypted_client_secret = f.encrypt(secret.encode()).decode()
        
    def decrypt_secret(self) -> str:
        """Decrypt client secret"""
        f = Fernet(self._encryption_key)
        return f.decrypt(self.encrypted_client_secret.encode()).decode()
        
    def __repr__(self):
        return f"<EHRConnection({self.organization_name} - {self.ehr_system.value})>"