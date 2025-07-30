from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.db.base import Base


class SSEEvent(Base):
    __tablename__ = "sse_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)