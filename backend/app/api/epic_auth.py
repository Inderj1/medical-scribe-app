from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.db.session import get_db
from app.core.config import settings
from app.integrations.epic_smart_connector import EpicSMARTConnector
from app.integrations.base import EHRCredentials
from app.schemas.epic_auth import TokenExchangeRequest, TokenExchangeResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/epic/token", response_model=TokenExchangeResponse)
async def exchange_epic_token(
    request: TokenExchangeRequest,
    db: Session = Depends(get_db)
):
    """Exchange Epic authorization code for access token"""
    try:
        # Create Epic SMART connector
        credentials = EHRCredentials(
            client_id=settings.EPIC_CLIENT_ID,
            client_secret=settings.EPIC_CLIENT_SECRET,
            base_url=settings.EPIC_BASE_URL
        )
        
        connector = EpicSMARTConnector(credentials)
        
        # Exchange code for token
        token_result = await connector.exchange_code_for_token(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        # Extract context
        context = token_result.get('context', {})
        
        # If we have a patient context, get patient details
        patient_data = None
        if context.get('patient'):
            try:
                connector._access_token = token_result['access_token']
                patient_data = await connector.get_patient(context['patient'])
            except Exception as e:
                logger.error(f"Failed to fetch patient data: {e}")
        
        return TokenExchangeResponse(
            access_token=token_result['access_token'],
            expires_in=token_result.get('expires_in', 3600),
            refresh_token=context.get('refresh_token'),
            patient=context.get('patient'),
            encounter=context.get('encounter'),
            practitioner=context.get('practitioner'),
            scope=context.get('scope', []),
            patient_data=patient_data
        )
        
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange token: {str(e)}"
        )


@router.post("/epic/refresh")
async def refresh_epic_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh Epic access token"""
    try:
        credentials = EHRCredentials(
            client_id=settings.EPIC_CLIENT_ID,
            client_secret=settings.EPIC_CLIENT_SECRET,
            base_url=settings.EPIC_BASE_URL
        )
        
        connector = EpicSMARTConnector(credentials)
        
        # Refresh token
        result = await connector.refresh_access_token(refresh_token)
        
        return {
            "access_token": result['access_token'],
            "expires_in": result['expires_in'],
            "refresh_token": result.get('refresh_token', refresh_token)
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.get("/epic/launch")
async def launch_epic_oauth(
    iss: str = None,
    launch: str = None
):
    """Initiate Epic OAuth2 authorization flow"""
    try:
        import secrets
        import urllib.parse
        
        # Generate state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": settings.EPIC_CLIENT_ID,
            "redirect_uri": settings.EPIC_REDIRECT_URI,
            "scope": settings.EPIC_SCOPE,
            "state": state,
            "aud": "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
        }
        
        # Remove any None values
        auth_params = {k: v for k, v in auth_params.items() if v is not None}
        
        # Add SMART launch parameters if provided
        if iss:
            auth_params["iss"] = iss
        if launch:
            auth_params["launch"] = launch
            
        auth_url = f"{settings.EPIC_AUTHORIZE_ENDPOINT}?{urllib.parse.urlencode(auth_params)}"
        
        return {
            "authorization_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        logger.error(f"Failed to create Epic launch URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create authorization URL: {str(e)}"
        )


@router.get("/epic/configuration")
async def get_epic_configuration():
    """Get Epic SMART configuration"""
    try:
        credentials = EHRCredentials(
            client_id=settings.EPIC_CLIENT_ID,
            client_secret=settings.EPIC_CLIENT_SECRET,
            base_url=settings.EPIC_BASE_URL
        )
        
        connector = EpicSMARTConnector(credentials)
        
        # Get SMART configuration
        config = await connector.get_smart_configuration()
        
        return {
            "authorization_endpoint": config.get("authorization_endpoint"),
            "token_endpoint": config.get("token_endpoint"),
            "introspection_endpoint": config.get("introspection_endpoint"),
            "capabilities": config.get("capabilities", []),
            "scopes_supported": config.get("scopes_supported", [])
        }
        
    except Exception as e:
        logger.error(f"Failed to get Epic configuration: {e}")
        return {
            "error": "Configuration unavailable",
            "fallback_auth_endpoint": f"{settings.EPIC_BASE_URL}/oauth2/authorize",
            "fallback_token_endpoint": f"{settings.EPIC_BASE_URL}/oauth2/token"
        }