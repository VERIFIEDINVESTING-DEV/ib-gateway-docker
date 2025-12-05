"""
Health check endpoint for IB API.

This endpoint is PUBLIC (no authentication required) and is used by:
- Docker health checks
- Load balancers
- Monitoring systems
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ib_client import get_ib_client


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str  # "healthy", "degraded", or "unhealthy"
    connected: bool
    account_ready: bool
    account_id: str | None
    trading_mode: str
    gateway_host: str
    gateway_port: int
    last_error: str | None = None


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy or degraded"},
    },
)
async def health_check() -> JSONResponse:
    """
    Health check endpoint.
    
    Returns the connection status to IB Gateway. This endpoint is public
    and does not require authentication.
    
    Status codes:
    - 200: Connected and account data ready
    - 503: Not connected or account data not ready
    
    Status values:
    - "healthy": Connected and account data available
    - "degraded": Connected but account data not yet received
    - "unhealthy": Not connected to IB Gateway
    """
    try:
        client = get_ib_client()
        status_data = client.get_connection_status()
        
        # Determine health status
        if status_data["connected"] and status_data["account_ready"]:
            health_status = "healthy"
            http_status = status.HTTP_200_OK
        elif status_data["connected"]:
            health_status = "degraded"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            health_status = "unhealthy"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        
        response = HealthResponse(
            status=health_status,
            connected=status_data["connected"],
            account_ready=status_data["account_ready"],
            account_id=status_data["account_id"],
            trading_mode=status_data["trading_mode"],
            gateway_host=status_data["gateway_host"],
            gateway_port=status_data["gateway_port"],
            last_error=status_data["last_error"],
        )
        
        return JSONResponse(
            status_code=http_status,
            content=response.model_dump(),
        )
        
    except RuntimeError:
        # IBClient not initialized yet
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "connected": False,
                "account_ready": False,
                "account_id": None,
                "trading_mode": "unknown",
                "gateway_host": "unknown",
                "gateway_port": 0,
                "last_error": "IB client not initialized",
            },
        )
