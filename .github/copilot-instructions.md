# IB Gateway Docker - AI Coding Instructions

## Project Overview

This project provides Docker images to run **Interactive Brokers Gateway/TWS** headlessly with automated login via [IBC](https://github.com/IbcAlpha/IBC). It includes an `algo-trader/` Python client for the TWS API.

## Architecture

### Two Docker Images
- **ib-gateway** (`docker-compose.yml`) - Headless IB Gateway with Xvfb + VNC
- **tws-rdesktop** (`tws-docker-compose.yml`) - Full TWS with xrdp/xfce desktop

### Version Channels
- `stable/` and `latest/` directories contain channel-specific Dockerfiles and configs
- Use `./update.sh <channel> <version>` to sync `image-files/` templates into channel directories

### Port Mapping (Critical!)
| External | Internal | Mode |
|----------|----------|------|
| 4001 | 4003 | Live API |
| 4002 | 4004 | Paper API |
| 5900 | 5900 | VNC |

**Always connect to external ports** (4001/4002) from client applications.

## Key Files & Patterns

### Configuration Flow
1. `.env` file → environment variables
2. `run.sh` → reads env, calls `common.sh` functions
3. `common.sh:apply_settings()` → generates `config.ini` and `jts.ini` from `.tmpl` templates using `envsubst`

### Template Files (in `*/config/`)
- `ibc/config.ini.tmpl` - IBC automation settings (login, 2FA handling)
- `ibgateway/jts.ini.tmpl` - TWS/Gateway settings (timezone, display)

### Docker Secrets Pattern
Use `_FILE` suffix for secrets: `TWS_PASSWORD_FILE`, `VNC_SERVER_PASSWORD_FILE`
```bash
# common.sh implements file_env() for this pattern
file_env 'TWS_PASSWORD'  # Reads from TWS_PASSWORD or TWS_PASSWORD_FILE
```

## algo-trader/ Python Client

### TWS API Pattern
```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
    
    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        # Error codes 2104, 2106, 2158 are INFO (connection OK), not errors
        pass
    
    def nextValidId(self, orderId):
        # Connection established - safe to start API calls
        self.start()
```

### Connection Settings (`algo-trader/config.py`)
- Paper trading: port `4002`
- Live trading: port `4001`
- Client ID `0` enables TWS order binding

## Development Commands

```bash
# Start IB Gateway container
docker compose up -d

# View logs
docker logs algo-trader-ib-gateway-1

# Connect via VNC (paper mode)
# Host: localhost:5900, Password: from VNC_SERVER_PASSWORD

# Run Python client
cd algo-trader && python account_balance.py

# Update Dockerfiles from templates
./update.sh latest 10.41.1e
```

## Environment Variables

Essential vars in `.env`:
- `TWS_USERID` / `TWS_PASSWORD` - IBKR credentials
- `TRADING_MODE` - `paper`, `live`, or `both`
- `VNC_SERVER_PASSWORD` - VNC access (omit to disable)
- `AUTO_RESTART_TIME` - Daily restart (e.g., `11:59 PM`)
- `TWOFA_TIMEOUT_ACTION` - `restart` or `exit`

## Common Gotchas

1. **Port confusion**: External 4001/4002 map to internal 4003/4004 via socat
2. **2FA handling**: Set `TWOFA_TIMEOUT_ACTION=restart` and `RELOGIN_AFTER_TWOFA_TIMEOUT=yes`
3. **Settings persistence**: Mount `TWS_SETTINGS_PATH` to a volume
4. **API error 2107**: "HMDS inactive" is normal - historical data connects on-demand
5. **Custom configs**: Set `CUSTOM_CONFIG=yes` and mount your own config files
