"""
Account Balance Fetcher for Interactive Brokers TWS API

This script connects to IB Gateway and fetches account information including:
- Net Liquidation Value
- Cash Balances
- Buying Power
- Current Positions

Based on IBKR's official tutorial:
https://www.interactivebrokers.com/campus/trading-lessons/python-account-portfolio/
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from threading import Timer
from decimal import Decimal
import config


class AccountApp(EWrapper, EClient):
    """TWS API Application for fetching account data."""

    def __init__(self):
        EClient.__init__(self, self)
        self.account_values = {}
        self.positions = []
        self.account_name = ""

    # ========== Error Handling ==========

    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        """Handle errors and notifications from TWS."""
        # Codes 2104, 2106, 2158 are just notifications that connection is OK
        if errorCode in [2104, 2106, 2158]:
            print(f"[INFO] {errorString}")
        else:
            print(f"[ERROR] ReqId: {reqId}, Code: {errorCode}, Msg: {errorString}")

    # ========== Connection Callbacks ==========

    def nextValidId(self, orderId):
        """Called when connection is established. Start requesting data."""
        print(f"\n{'='*60}")
        print("Connected to IB Gateway!")
        print(f"Next Valid Order ID: {orderId}")
        print(f"{'='*60}\n")
        self.start()

    def connectAck(self):
        """Acknowledge connection."""
        print("[CONNECTING] Connection acknowledged...")

    # ========== Account Data Callbacks ==========

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Receive account value updates."""
        self.account_name = accountName

        # Store all values, organized by key
        if key not in self.account_values:
            self.account_values[key] = {}
        self.account_values[key][currency] = val

        # Print key account metrics as they arrive
        important_keys = [
            "NetLiquidation",
            "TotalCashValue",
            "BuyingPower",
            "AvailableFunds",
            "CashBalance",
            "UnrealizedPnL",
            "RealizedPnL"
        ]

        if key in important_keys and currency:
            print(f"  {key}: {val} {currency}")

    def updatePortfolio(self, contract: Contract, position: Decimal,
                       marketPrice: float, marketValue: float,
                       averageCost: float, unrealizedPNL: float,
                       realizedPNL: float, accountName: str):
        """Receive portfolio position updates."""
        self.positions.append({
            "symbol": contract.symbol,
            "secType": contract.secType,
            "exchange": contract.exchange,
            "position": position,
            "marketPrice": marketPrice,
            "marketValue": marketValue,
            "averageCost": averageCost,
            "unrealizedPNL": unrealizedPNL,
            "realizedPNL": realizedPNL
        })

    def updateAccountTime(self, timeStamp: str):
        """Receive account update timestamp."""
        print(f"\n[TIMESTAMP] Account data as of: {timeStamp}")

    def accountDownloadEnd(self, accountName: str):
        """Called when all account data has been received."""
        print(f"\n{'='*60}")
        print(f"Account Download Complete: {accountName}")
        print(f"{'='*60}")
        self.print_summary()

    # ========== Helper Methods ==========

    def print_summary(self):
        """Print a formatted summary of account data."""
        print("\n" + "="*60)
        print("📊 ACCOUNT SUMMARY")
        print("="*60)

        # Key metrics to display
        summary_keys = [
            ("NetLiquidation", "Net Liquidation Value"),
            ("TotalCashValue", "Total Cash Value"),
            ("BuyingPower", "Buying Power"),
            ("AvailableFunds", "Available Funds"),
            ("GrossPositionValue", "Gross Position Value"),
            ("MaintMarginReq", "Maintenance Margin"),
            ("UnrealizedPnL", "Unrealized P&L"),
            ("RealizedPnL", "Realized P&L"),
        ]

        for key, label in summary_keys:
            if key in self.account_values:
                for currency, value in self.account_values[key].items():
                    if currency:  # Skip empty currency entries
                        print(f"  {label}: {value} {currency}")

        # Print cash balances
        if "CashBalance" in self.account_values:
            print("\n💰 CASH BALANCES:")
            for currency, value in self.account_values["CashBalance"].items():
                if currency and float(value) != 0:
                    print(f"  {currency}: {value}")

        # Print positions
        if self.positions:
            print("\n📈 POSITIONS:")
            for pos in self.positions:
                print(f"  {pos['symbol']} ({pos['secType']}): "
                      f"{pos['position']} @ ${pos['averageCost']:.2f} | "
                      f"P&L: ${pos['unrealizedPNL']:.2f}")
        else:
            print("\n📈 POSITIONS: None")

        print("\n" + "="*60)

    # ========== Control Methods ==========

    def start(self):
        """Start requesting account data."""
        print("[REQUESTING] Account updates...")
        print("-"*60)

        # Request account updates
        # Pass empty string for account to use the logged-in account
        self.reqAccountUpdates(True, "")

    def stop(self):
        """Stop account updates and disconnect."""
        print("\n[STOPPING] Cancelling subscriptions...")
        self.reqAccountUpdates(False, "")
        self.done = True
        self.disconnect()


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🚀 IB Gateway Account Balance Fetcher")
    print("="*60)
    print(f"Connecting to {config.TWS_HOST}:{config.TWS_PORT}")
    print(f"Client ID: {config.CLIENT_ID}")
    print("="*60 + "\n")

    # Create application instance
    app = AccountApp()

    # Connect to IB Gateway
    app.connect(config.TWS_HOST, config.TWS_PORT, config.CLIENT_ID)

    # Set a timer to stop after collecting data
    Timer(config.ACCOUNT_DATA_TIMEOUT, app.stop).start()

    # Start the message processing loop
    app.run()

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
