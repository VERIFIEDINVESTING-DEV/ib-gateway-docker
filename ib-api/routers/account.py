"""
Account endpoints for IB API.

All endpoints in this router require JWT authentication.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import User, get_current_user
from ib_client import get_ib_client


router = APIRouter(prefix="/account", tags=["Account"])


# =============================================================================
# Response Models
# =============================================================================

class AccountValue(BaseModel):
    """A single account value with currency."""
    value: str
    currency: str


class Position(BaseModel):
    """A portfolio position."""
    symbol: str
    secType: str
    exchange: str
    currency: str
    position: float
    marketPrice: float
    marketValue: float
    averageCost: float
    unrealizedPNL: float
    realizedPNL: float


class AccountBalanceResponse(BaseModel):
    """Account balance response model."""
    account_id: str
    last_update: str
    connected: bool
    trading_mode: str
    summary: dict[str, AccountValue]
    cash_balances: dict[str, str]
    positions: list[Position]


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/balance",
    response_model=AccountBalanceResponse,
    responses={
        200: {"description": "Account balance retrieved successfully"},
        401: {"description": "Not authenticated"},
        503: {"description": "Not connected to IB Gateway"},
    },
)
async def get_account_balance(
    current_user: Annotated[User, Depends(get_current_user)]
) -> AccountBalanceResponse:
    """
    Get account balance and positions.
    
    Requires JWT authentication. Returns:
    - Account summary (net liquidation, buying power, etc.)
    - Cash balances by currency
    - Current positions with P&L
    
    **Note**: Data is updated in real-time from IB Gateway. The `last_update`
    field shows when the data was last received from IBKR.
    """
    try:
        client = get_ib_client()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IB client not initialized",
        )
    
    if not client.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Not connected to IB Gateway",
        )
    
    account_data = client.get_account_summary()
    
    # Convert positions to Pydantic models
    positions = [Position(**pos) for pos in account_data["positions"]]
    
    # Convert summary values to AccountValue models
    summary = {
        key: AccountValue(**val) 
        for key, val in account_data["summary"].items()
    }
    
    return AccountBalanceResponse(
        account_id=account_data["account_id"],
        last_update=account_data["last_update"],
        connected=account_data["connected"],
        trading_mode=account_data["trading_mode"],
        summary=summary,
        cash_balances=account_data["cash_balances"],
        positions=positions,
    )


@router.get(
    "/summary",
    responses={
        200: {"description": "Account summary retrieved successfully"},
        401: {"description": "Not authenticated"},
        503: {"description": "Not connected to IB Gateway"},
    },
)
async def get_account_summary(
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict[str, Any]:
    """
    Get a simplified account summary.
    
    Requires JWT authentication. Returns key metrics only:
    - Net Liquidation Value
    - Buying Power
    - Available Funds
    - Unrealized P&L
    
    For full details including positions, use `/account/balance`.
    """
    try:
        client = get_ib_client()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IB client not initialized",
        )
    
    if not client.is_connected():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Not connected to IB Gateway",
        )
    
    account_data = client.get_account_summary()
    
    # Return simplified summary
    return {
        "account_id": account_data["account_id"],
        "trading_mode": account_data["trading_mode"],
        "last_update": account_data["last_update"],
        "net_liquidation": account_data["summary"].get("NetLiquidation"),
        "buying_power": account_data["summary"].get("BuyingPower"),
        "available_funds": account_data["summary"].get("AvailableFunds"),
        "unrealized_pnl": account_data["summary"].get("UnrealizedPnL"),
        "realized_pnl": account_data["summary"].get("RealizedPnL"),
        "position_count": len(account_data["positions"]),
    }
