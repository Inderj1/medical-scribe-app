from pydantic import BaseModel
from typing import Optional, List, Any


class TokenExchangeRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str


class TokenExchangeResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    patient: Optional[str] = None
    encounter: Optional[str] = None
    practitioner: Optional[str] = None
    scope: List[str] = []
    patient_data: Optional[Any] = None