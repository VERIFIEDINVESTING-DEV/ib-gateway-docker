"""
Account endpoints for IB API.

All endpoints in this router require JWT authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import User, get_current_user
from ib_client import IBClient, get_ib_client


router = APIRouter(prefix="/account", tags=["Account"])


# =============================================================================
# Response Models
# =============================================================================

class AccountValue(BaseModel):
    """A single account value with currency."""
    value: str
    currency: str


class AccountValueNumeric(BaseModel):
    """A numeric account value with currency, with safe defaults."""
    value: float = 0.0
    currency: str = "USD"


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


class AccountSummaryResponse(BaseModel):
    """Simplified account summary response with typed fields."""
    account_id: str
    trading_mode: str
    last_update: str
    net_liquidation: AccountValueNumeric
    buying_power: AccountValueNumeric
    available_funds: AccountValueNumeric
    unrealized_pnl: AccountValueNumeric
    realized_pnl: AccountValueNumeric
    position_count: int = 0


# =============================================================================
# Dependencies
# =============================================================================

def get_connected_ib_client() -> IBClient:
    """
    Dependency that returns a connected IB client.
    
    Raises:
        HTTPException 503: If client is not initialized or not connected
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
    
    return client


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_numeric_value(
    summary: dict, 
    key: str, 
    default_currency: str = "USD"
) -> AccountValueNumeric:
    """
    Extract a numeric value from the summary dict with safe defaults.
    
    Converts string values to float, handles missing keys gracefully.
    """
    if key not in summary:
        return AccountValueNumeric(value=0.0, currency=default_currency)
    
    raw = summary[key]
    try:
        # raw is {"value": "123.45", "currency": "USD"}
        value = float(raw.get("value", 0.0))
        currency = raw.get("currency", default_currency)
        return AccountValueNumeric(value=value, currency=currency)
    except (ValueError, TypeError, AttributeError):
        return AccountValueNumeric(value=0.0, currency=default_currency)


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
    current_user: Annotated[User, Depends(get_current_user)],
    client: Annotated[IBClient, Depends(get_connected_ib_client)],
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
    response_model=AccountSummaryResponse,
    responses={
        200: {"description": "Account summary retrieved successfully"},
        401: {"description": "Not authenticated"},
        503: {"description": "Not connected to IB Gateway"},
    },
)
async def get_account_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    client: Annotated[IBClient, Depends(get_connected_ib_client)],
) -> AccountSummaryResponse:
    """
    Get a simplified account summary.
    
    Requires JWT authentication. Returns key metrics only:
    - Net Liquidation Value
    - Buying Power
    - Available Funds
    - Unrealized P&L
    
    For full details including positions, use `/account/balance`.
    """
    account_data = client.get_account_summary()
    summary = account_data["summary"]
    
    return AccountSummaryResponse(
        account_id=account_data["account_id"],
        trading_mode=account_data["trading_mode"],
        last_update=account_data["last_update"],
        net_liquidation=_extract_numeric_value(summary, "NetLiquidation"),
        buying_power=_extract_numeric_value(summary, "BuyingPower"),
        available_funds=_extract_numeric_value(summary, "AvailableFunds"),
        unrealized_pnl=_extract_numeric_value(summary, "UnrealizedPnL"),
        realized_pnl=_extract_numeric_value(summary, "RealizedPnL"),
        position_count=len(account_data["positions"]),
    )
