from fastapi import APIRouter, HTTPException, Request, Response
from typing import Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

EHRBASE_BASE_URL = "https://294c4163c972.ngrok.app/ehrbase"

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def ehrbase_proxy(
    path: str,
    request: Request,
    response: Response
):
    """
    Proxy requests to EHRBASE server to avoid CORS issues
    """
    try:
        # Build the target URL
        target_url = f"{EHRBASE_BASE_URL}/{path}"
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        # Get headers from the original request (excluding host-related headers)
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ['host', 'connection', 'content-length']
        }
        
        # Add basic authentication for EHRBASE
        import base64
        auth_string = base64.b64encode(b'ehrbase:secret').decode('ascii')
        headers['Authorization'] = f'Basic {auth_string}'
        
        # Read request body if present
        body = None
        if request.method in ["POST", "PUT"]:
            body = await request.body()
        
        # Make the request to EHRBASE
        async with httpx.AsyncClient(verify=False) as client:
            ehrbase_response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
                timeout=30.0
            )
        
        # Set CORS headers for the response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
        
        # Copy response headers from EHRBASE (excluding some headers)
        for key, value in ehrbase_response.headers.items():
            if key.lower() not in ['content-encoding', 'content-length', 'connection']:
                response.headers[key] = value
        
        # Return the response
        return Response(
            content=ehrbase_response.content,
            status_code=ehrbase_response.status_code,
            headers=response.headers
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while proxying request to EHRBASE: {target_url}")
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to EHRBASE: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in EHRBASE proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Check if EHRBASE is accessible through the proxy
    """
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                EHRBASE_BASE_URL,
                timeout=10.0
            )
        return {
            "status": "healthy",
            "ehrbase_url": EHRBASE_BASE_URL,
            "ehrbase_status": response.status_code
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "ehrbase_url": EHRBASE_BASE_URL,
            "error": str(e)
        }