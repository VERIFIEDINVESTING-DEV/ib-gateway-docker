"""
Configuration settings for TWS API connection.
"""

# Connection Settings
TWS_HOST = "ib-gateway.host.verifiedinvesting.com"

# Port configuration:
# - 4001: Live trading (maps to internal 4003)
# - 4002: Paper trading (maps to internal 4004)
TWS_PORT = 4002  # Paper trading by default

# Client ID - Use 0 for full functionality including manual TWS order binding
CLIENT_ID = 0

# Timeout settings (in seconds)
CONNECTION_TIMEOUT = 10
ACCOUNT_DATA_TIMEOUT = 5
