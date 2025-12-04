"""
Basic Connection Test for IB Gateway

A minimal example to verify connectivity to IB Gateway.
"""

import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from threading import Timer
import config


class TestConnection(EWrapper, EClient):
    """Simple connection test."""
    
    def __init__(self):
        EClient.__init__(self, self)
        
    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        """Handle errors."""
        if errorCode in [2104, 2106, 2158]:
            print(f"✅ {errorString}")
        else:
            print(f"❌ Error {errorCode}: {errorString}")
    
    def nextValidId(self, orderId):
        """Connection successful."""
        print(f"\n{'='*50}")
        print("🎉 CONNECTION SUCCESSFUL!")
        print(f"{'='*50}")
        print(f"Next Valid Order ID: {orderId}")
        print(f"{'='*50}\n")
        
    def currentTime(self, time):
        """Receive server time."""
        from datetime import datetime
        dt = datetime.fromtimestamp(time)
        print(f"📅 Server Time: {dt}")


def main():
    print("\n" + "="*50)
    print("🔌 IB Gateway Connection Test")
    print("="*50)
    print(f"Host: {config.TWS_HOST}")
    print(f"Port: {config.TWS_PORT}")
    print(f"Client ID: {config.CLIENT_ID}")
    print("="*50 + "\n")
    
    app = TestConnection()
    app.connect(config.TWS_HOST, config.TWS_PORT, config.CLIENT_ID)
    
    # Request server time to verify connection
    def request_time():
        if app.isConnected():
            app.reqCurrentTime()
    
    def disconnect():
        print("\nDisconnecting...")
        app.disconnect()
    
    Timer(1, request_time).start()
    Timer(3, disconnect).start()
    
    app.run()
    print("✅ Test complete!")


if __name__ == "__main__":
    main()
