"""
Thread-safe IB Gateway client for FastAPI integration.

This module provides a singleton IBClient that:
- Connects to IB Gateway in a background thread
- Maintains thread-safe access to account data
- Provides methods for FastAPI endpoints to query data
"""

import logging
import threading
from decimal import Decimal
from typing import Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from config import Settings


# Configure logging
logger = logging.getLogger(__name__)


class IBClient(EWrapper, EClient):
    """
    Thread-safe Interactive Brokers API client.

    Runs the TWS API message loop in a background thread while providing
    thread-safe access to account data for FastAPI endpoints.
    """

    def __init__(self, settings: Settings):
        EWrapper.__init__(self)
        EClient.__init__(self, self)

        self.settings = settings

        # Thread synchronization
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._account_ready = threading.Event()

        # Thread for running the message loop
        self._thread: threading.Thread | None = None

        # Account data (protected by _lock)
        self._account_values: dict[str, dict[str, str]] = {}
        self._positions: list[dict[str, Any]] = []
        self._account_name: str = ""
        self._account_time: str = ""
        self._next_order_id: int = 0

        # Error tracking
        self._last_error: str | None = None

    # =========================================================================
    # Connection Management
    # =========================================================================

    def start(self) -> bool:
        """
        Connect to IB Gateway and start the message processing thread.

        Returns:
            True if connection successful, False otherwise
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("IBClient already running")
            return True

        logger.info(
            f"Connecting to IB Gateway at {self.settings.ib_gateway_host}:"
            f"{self.settings.ib_gateway_port} (mode: {self.settings.trading_mode})"
        )

        try:
            self.connect(
                self.settings.ib_gateway_host,
                self.settings.ib_gateway_port,
                self.settings.ib_client_id
            )
        except Exception as e:
            logger.error(f"Failed to connect to IB Gateway: {e}")
            return False

        # Start the message processing thread
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

        # Wait for connection to be established
        if not self._connected.wait(timeout=self.settings.ib_connection_timeout):
            logger.error("Connection timeout - IB Gateway did not respond")
            self.stop()
            return False

        logger.info("Successfully connected to IB Gateway")

        # Request account updates
        self.reqAccountUpdates(True, "")

        return True

    def stop(self) -> None:
        """Disconnect from IB Gateway and stop the message thread."""
        logger.info("Stopping IBClient...")

        try:
            # Stop account updates
            if self.isConnected():
                self.reqAccountUpdates(False, "")
                self.disconnect()
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

        # Clear connection state
        self._connected.clear()
        self._account_ready.clear()

        # Wait for thread to finish
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._thread = None
        logger.info("IBClient stopped")

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway."""
        return self._connected.is_set() and self.isConnected()

    # =========================================================================
    # EWrapper Callbacks - Connection
    # =========================================================================

    def connectAck(self) -> None:
        """Called when connection is acknowledged."""
        logger.debug("Connection acknowledged")

    def nextValidId(self, orderId: int) -> None:
        """Called when connection is fully established."""
        with self._lock:
            self._next_order_id = orderId
        self._connected.set()
        logger.info(f"Connected - next valid order ID: {orderId}")

    def connectionClosed(self) -> None:
        """Called when connection is closed."""
        self._connected.clear()
        self._account_ready.clear()
        logger.warning("Connection to IB Gateway closed")

    # =========================================================================
    # EWrapper Callbacks - Errors
    # =========================================================================

    def error(self, reqId: int, errorCode: int, errorString: str,
              advancedOrderReject: str = "") -> None:
        """Handle errors and notifications from TWS."""
        # These are informational messages, not errors
        info_codes = {2104, 2106, 2158, 2107}

        if errorCode in info_codes:
            logger.debug(f"[INFO {errorCode}] {errorString}")
        else:
            logger.error(f"[ERROR {errorCode}] ReqId: {reqId}, Msg: {errorString}")
            with self._lock:
                self._last_error = f"Error {errorCode}: {errorString}"

    # =========================================================================
    # EWrapper Callbacks - Account Data
    # =========================================================================

    def updateAccountValue(self, key: str, val: str, currency: str,
                          accountName: str) -> None:
        """Receive account value updates."""
        with self._lock:
            self._account_name = accountName
            if key not in self._account_values:
                self._account_values[key] = {}
            self._account_values[key][currency] = val

    def updatePortfolio(self, contract: Contract, position: Decimal,
                       marketPrice: float, marketValue: float,
                       averageCost: float, unrealizedPNL: float,
                       realizedPNL: float, accountName: str) -> None:
        """Receive portfolio position updates."""
        # Skip closed positions
        if float(position) == 0:
            with self._lock:
                # Remove position if it exists
                self._positions = [
                    pos for pos in self._positions
                    if not (pos["symbol"] == contract.symbol and
                           pos["secType"] == contract.secType)
                ]
            return

        position_data = {
            "symbol": contract.symbol,
            "secType": contract.secType,
            "exchange": contract.exchange,
            "currency": contract.currency,
            "position": float(position),
            "marketPrice": marketPrice,
            "marketValue": marketValue,
            "averageCost": averageCost,
            "unrealizedPNL": unrealizedPNL,
            "realizedPNL": realizedPNL,
        }

        with self._lock:
            # Update existing position or add new one
            for i, pos in enumerate(self._positions):
                if (pos["symbol"] == contract.symbol and
                    pos["secType"] == contract.secType):
                    self._positions[i] = position_data
                    return
            self._positions.append(position_data)

    def updateAccountTime(self, timeStamp: str) -> None:
        """Receive account update timestamp."""
        with self._lock:
            self._account_time = timeStamp

    def accountDownloadEnd(self, accountName: str) -> None:
        """Called when all account data has been received."""
        self._account_ready.set()
        logger.info(f"Account data download complete for {accountName}")

    # =========================================================================
    # Public API Methods (Thread-Safe)
    # =========================================================================

    def get_account_summary(self) -> dict[str, Any]:
        """
        Get a summary of account data.

        Returns:
            Dictionary with account values, positions, and metadata
        """
        with self._lock:
            # Extract key metrics
            summary = {}
            key_metrics = [
                "NetLiquidation",
                "TotalCashValue",
                "BuyingPower",
                "AvailableFunds",
                "GrossPositionValue",
                "MaintMarginReq",
                "UnrealizedPnL",
                "RealizedPnL",
            ]

            for key in key_metrics:
                if key in self._account_values:
                    # Get USD value if available, otherwise first currency
                    values = self._account_values[key]
                    if "USD" in values:
                        summary[key] = {"value": values["USD"], "currency": "USD"}
                    elif "BASE" in values:
                        summary[key] = {"value": values["BASE"], "currency": "BASE"}
                    elif values:
                        # Get first non-empty value
                        for curr, val in values.items():
                            if curr:
                                summary[key] = {"value": val, "currency": curr}
                                break

            # Get cash balances
            cash_balances = {}
            if "CashBalance" in self._account_values:
                for currency, value in self._account_values["CashBalance"].items():
                    if currency and float(value) != 0:
                        cash_balances[currency] = value

            return {
                "account_id": self._account_name,
                "last_update": self._account_time,
                "connected": self.is_connected(),
                "trading_mode": self.settings.trading_mode,
                "summary": summary,
                "cash_balances": cash_balances,
                "positions": list(self._positions),  # Copy the list
            }

    def get_connection_status(self) -> dict[str, Any]:
        """
        Get connection status for health check.

        Returns:
            Dictionary with connection state and metadata
        """
        with self._lock:
            return {
                "connected": self.is_connected(),
                "account_ready": self._account_ready.is_set(),
                "account_id": self._account_name or None,
                "trading_mode": self.settings.trading_mode,
                "gateway_host": self.settings.ib_gateway_host,
                "gateway_port": self.settings.ib_gateway_port,
                "last_error": self._last_error,
            }


# =============================================================================
# Singleton Instance
# =============================================================================

# Global client instance (initialized in FastAPI lifespan)
_client: IBClient | None = None


def get_ib_client() -> IBClient:
    """
    Get the global IBClient instance.

    Raises:
        RuntimeError: If client hasn't been initialized
    """
    if _client is None:
        raise RuntimeError("IBClient not initialized. Call init_ib_client() first.")
    return _client


def init_ib_client(settings: Settings) -> IBClient:
    """
    Initialize the global IBClient instance.

    Called during FastAPI startup.
    """
    global _client
    _client = IBClient(settings)
    return _client


def shutdown_ib_client() -> None:
    """
    Shutdown the global IBClient instance.

    Called during FastAPI shutdown.
    """
    global _client
    if _client is not None:
        _client.stop()
        _client = None
