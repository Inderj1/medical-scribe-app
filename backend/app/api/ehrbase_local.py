from fastapi import APIRouter, HTTPException, Request, Response
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

LOCAL_EHRBASE_URL = "http://host.docker.internal:5000/api"

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def ehrbase_local_proxy(
    path: str,
    request: Request,
    response: Response
):
    """
    Proxy requests to local EHRBASE API running on port 5000
    """
    try:
        # Build the target URL
        target_url = f"{LOCAL_EHRBASE_URL}/{path}"
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        # Get headers from the original request (excluding host-related headers)
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ['host', 'connection', 'content-length']
        }
        
        # Read request body if present
        body = None
        if request.method in ["POST", "PUT"]:
            body = await request.body()
        
        # Make the request to local EHRBASE
        async with httpx.AsyncClient() as client:
            local_response = await client.request(
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
        
        # Copy response headers from local EHRBASE (excluding some headers)
        for key, value in local_response.headers.items():
            if key.lower() not in ['content-encoding', 'content-length', 'connection']:
                response.headers[key] = value
        
        # Return the response
        return Response(
            content=local_response.content,
            status_code=local_response.status_code,
            headers=response.headers
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while proxying request to local EHRBASE: {target_url}")
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to local EHRBASE: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in local EHRBASE proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Check if local EHRBASE is accessible
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LOCAL_EHRBASE_URL}/patients",
                timeout=10.0
            )
        return {
            "status": "healthy",
            "local_ehrbase_url": LOCAL_EHRBASE_URL,
            "local_ehrbase_status": response.status_code
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "local_ehrbase_url": LOCAL_EHRBASE_URL,
            "error": str(e)
        }