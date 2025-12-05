"""
IB API - FastAPI wrapper for Interactive Brokers Gateway.

This is the main application entry point. It:
- Initializes the IB Gateway connection on startup
- Provides JWT-protected API endpoints
- Shuts down cleanly on exit
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse

from config import Settings, get_settings
from ib_client import init_ib_client, shutdown_ib_client
from auth import router as auth_router, verify_token
from routers.health import router as health_router
from routers.account import router as account_router


# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Handler
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    
    Startup:
    - Load settings
    - Initialize and connect to IB Gateway
    
    Shutdown:
    - Disconnect from IB Gateway
    - Cleanup resources
    """
    # Startup
    logger.info("=" * 60)
    logger.info("IB API Starting Up...")
    logger.info("=" * 60)
    
    settings = get_settings()
    logger.info(f"Trading mode: {settings.trading_mode}")
    logger.info(f"IB Gateway: {settings.ib_gateway_host}:{settings.ib_gateway_port}")
    
    # Initialize IB client
    client = init_ib_client(settings)
    
    # Attempt to connect (non-blocking - will retry in background if needed)
    connected = client.start()
    if connected:
        logger.info("Successfully connected to IB Gateway")
    else:
        logger.warning(
            "Failed to connect to IB Gateway on startup. "
            "The API will start but /health will report unhealthy. "
            "Check that IB Gateway is running and 2FA is approved."
        )
    
    logger.info("IB API Ready")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("IB API Shutting Down...")
    logger.info("=" * 60)
    
    shutdown_ib_client()
    
    logger.info("IB API Shutdown Complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="IB API",
    description=(
        "REST API wrapper for Interactive Brokers Gateway.\n\n"
        "## Authentication\n\n"
        "1. Get a JWT token: `POST /auth/token` with username/password\n"
        "2. Use the token: `Authorization: Bearer <token>`\n\n"
        "## Endpoints\n\n"
        "- `/health` - Connection status (public)\n"
        "- `/account/balance` - Account data (authenticated)\n"
        "- `/account/summary` - Key metrics (authenticated)\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Disable default docs - we'll create protected versions
    docs_url=None,
    redoc_url=None,
    # Keep OpenAPI schema available (needed for docs)
    openapi_url="/openapi.json",
)


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(account_router)


# =============================================================================
# Protected Documentation Routes
# =============================================================================

async def verify_docs_token(
    token: str = Query(..., description="JWT token for docs access"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Verify JWT token for documentation access."""
    try:
        verify_token(token, settings)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Get a token from POST /auth/token",
        )


@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
async def custom_swagger_ui(
    _: None = Depends(verify_docs_token),
) -> HTMLResponse:
    """
    Swagger UI documentation.
    
    Access with: GET /docs?token=<your-jwt-token>
    
    Get a token first: POST /auth/token with your credentials.
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


@app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
async def custom_redoc(
    _: None = Depends(verify_docs_token),
) -> HTMLResponse:
    """
    ReDoc documentation.
    
    Access with: GET /redoc?token=<your-jwt-token>
    
    Get a token first: POST /auth/token with your credentials.
    """
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect info."""
    return {
        "name": "IB API",
        "version": "1.0.0",
        "docs": "/docs?token=<jwt-token>",
        "health": "/health",
        "auth": "POST /auth/token",
    }
