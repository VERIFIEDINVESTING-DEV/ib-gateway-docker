# Plan: Add FastAPI Wrapper (`ib-api`) to IB Gateway Stack

**TL;DR:** Create a new `ib-api/` folder with a FastAPI server that connects to IB Gateway internally, uses JWT authentication, and exposes account balance + health check endpoints. IB Gateway has **zero public ports** - VNC accessed via SSH tunnel only. Trading mode controlled via environment variable at startup.

## Steps

### 1. Create `ib-api/` folder structure with FastAPI application

- `ib-api/Dockerfile` - Python 3.11 slim image with uvicorn
- `ib-api/requirements.txt` - fastapi, uvicorn, ibapi, python-jose[cryptography], passlib[bcrypt]
- `ib-api/main.py` - FastAPI app with lifespan handler, protected `/docs` route
- `ib-api/config.py` - Settings from environment (IB host/port, JWT secret, credentials)
- `ib-api/auth.py` - JWT token creation/validation, `POST /auth/token` endpoint
- `ib-api/ib_client.py` - Thread-safe IB Gateway wrapper with background thread
- `ib-api/routers/account.py` - `GET /account/balance` endpoint (JWT protected)
- `ib-api/routers/health.py` - `GET /health` endpoint (public, returns connection status)

### 2. Update `coolify-docker-compose.yml`

- **Remove ALL port mappings from `ib-gateway`** (completely internal, including VNC)
- Add `ib-api` service building from `./ib-api`
- Expose only `ib-api` on port 8000 (Coolify proxies to HTTPS)
- Add environment variables: `JWT_SECRET`, `API_USERNAME`, `API_PASSWORD`
- `ib-api` connects to `ib-gateway:4004` (paper) or `ib-gateway:4003` (live) based on `TRADING_MODE`
- Add comments documenting SSH tunnel for VNC access

### 3. Implement JWT auth in `ib-api/auth.py`

- `POST /auth/token` - accepts username/password, returns JWT
- JWT includes expiration (configurable, default 30 min)
- Dependency `get_current_user` validates JWT on protected routes

### 4. Implement IB client in `ib-api/ib_client.py`

- `IBClient` class extending `EWrapper` and `EClient`
- Runs `EClient.run()` in daemon thread started via FastAPI lifespan
- Thread-safe account data access via `threading.Lock`
- Methods: `get_account_summary()`, `is_connected()`

### 5. Protect Swagger docs in `ib-api/main.py`

- Disable default `/docs` and `/redoc` routes
- Create custom `/docs` route that requires valid JWT in query param or header

## VNC Access (SSH Tunnel)

```bash
# From any machine with SSH access:
ssh -L 5900:localhost:5900 root@host.verifiedinvesting.com

# Then connect VNC client to: localhost:5900
# Password: (your VNC_SERVER_PASSWORD)
```

## Further Considerations

1. **JWT Secret** - Should be a long random string (32+ chars). Will add generation command in comments.

2. **First-time 2FA** - After deploying, you'll need to SSH tunnel → VNC → approve 2FA once.

3. **API endpoint for future** - Easy to add more endpoints (positions, orders, market data) later.
