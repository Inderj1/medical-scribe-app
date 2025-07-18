import httpx
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import urlencode

from .epic_connector import EpicConnector
from .base import EHRCredentials

logger = logging.getLogger(__name__)


class EpicSMARTConnector(EpicConnector):
    """Epic connector with SMART on FHIR support"""
    
    def __init__(self, credentials: EHRCredentials):
        super().__init__(credentials)
        self.authorize_endpoint = f"{credentials.base_url}/oauth2/authorize"
        self.token_endpoint = f"{credentials.base_url}/oauth2/token"
        
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token (SMART on FHIR flow)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        'grant_type': 'authorization_code',
                        'code': code,
                        'redirect_uri': redirect_uri,
                        'client_id': self.credentials.client_id
                    },
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
                response.raise_for_status()
                
            token_data = response.json()
            
            # Extract token and context
            self._access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Extract SMART context
            context = {
                'patient': token_data.get('patient'),
                'encounter': token_data.get('encounter'),
                'practitioner': token_data.get('practitioner'),
                'need_patient_banner': token_data.get('need_patient_banner', True),
                'smart_style_url': token_data.get('smart_style_url'),
                'refresh_token': token_data.get('refresh_token'),
                'scope': token_data.get('scope', '').split(' ')
            }
            
            logger.info(f"Successfully exchanged code for token with patient context: {context.get('patient')}")
            
            return {
                'access_token': self._access_token,
                'expires_in': expires_in,
                'context': context
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise
            
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': refresh_token,
                        'client_id': self.credentials.client_id
                    },
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
                response.raise_for_status()
                
            token_data = response.json()
            
            # Update token
            self._access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                'access_token': self._access_token,
                'expires_in': expires_in,
                'refresh_token': token_data.get('refresh_token', refresh_token)
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise
            
    async def get_patient_context(self, access_token: str) -> Dict[str, Any]:
        """Get patient context from token introspection or user info endpoint"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Try userinfo endpoint
            userinfo_url = f"{self.credentials.base_url}/oauth2/userinfo"
            async with httpx.AsyncClient() as client:
                response = await client.get(userinfo_url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                    
            # Fallback: decode JWT if available
            try:
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                return decoded
            except:
                pass
                
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get patient context: {e}")
            return {}
            
    def build_authorization_url(self, 
                              launch_token: str,
                              state: str,
                              redirect_uri: str,
                              scope: str = "launch patient/*.read user/*.read openid profile") -> str:
        """Build Epic authorization URL for SMART launch"""
        params = {
            'response_type': 'code',
            'client_id': self.credentials.client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state,
            'launch': launch_token,
            'aud': f"{self.credentials.base_url}/api/FHIR/R4"
        }
        
        return f"{self.authorize_endpoint}?{urlencode(params)}"
        
    async def get_conformance_statement(self) -> Dict[str, Any]:
        """Get Epic's FHIR conformance/capability statement"""
        try:
            url = f"{self.credentials.base_url}/api/FHIR/R4/metadata"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers={'Accept': 'application/fhir+json'})
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Failed to get conformance statement: {e}")
            raise
            
    async def get_smart_configuration(self) -> Dict[str, Any]:
        """Get SMART configuration from well-known endpoint"""
        try:
            url = f"{self.credentials.base_url}/.well-known/smart-configuration"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Failed to get SMART configuration: {e}")
            raise