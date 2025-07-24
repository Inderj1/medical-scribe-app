"""Clerk authentication integration"""

from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Clerk configuration
CLERK_API_URL = "https://api.clerk.dev/v1"
CLERK_PUBLISHABLE_KEY = "pk_test_ZXhjaXRpbmctc2FsbW9uLTY3LmNsZXJrLmFjY291bnRzLmRldiQ"
CLERK_SECRET_KEY = None  # This should be in .env for production

class ClerkAuth(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(ClerkAuth, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super(ClerkAuth, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme."
                )
            
            # For development, we'll accept any token that looks like a Clerk token
            # In production, you would verify this with Clerk's API
            token = credentials.credentials
            
            # Basic validation - Clerk tokens are usually JWT format
            if token and len(token.split('.')) == 3:
                return token
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token format"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code."
            )

# Instance to use as dependency
clerk_auth = ClerkAuth()

async def get_current_clerk_user(token: str = Depends(clerk_auth)) -> Dict[str, Any]:
    """
    Get user information from Clerk token
    For development, we'll return a mock user
    In production, you would verify with Clerk's API
    """
    # Mock user for development
    return {
        "id": "clerk_user_123",
        "email": "user@example.com",
        "name": "Clerk User",
        "role": "physician"
    }

# WebSocket version that accepts token as query parameter
async def get_clerk_user_ws(token: str) -> Optional[Dict[str, Any]]:
    """Verify Clerk token for WebSocket connections"""
    if token and len(token.split('.')) == 3:
        # Mock user for development
        return {
            "id": "clerk_user_123",
            "email": "user@example.com", 
            "name": "Clerk User",
            "role": "physician"
        }
    return None