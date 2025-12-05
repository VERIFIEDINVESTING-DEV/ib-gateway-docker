"""
JWT Authentication for IB API.

Provides:
- POST /auth/token - Get JWT token with username/password
- get_current_user dependency for protected routes
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
import bcrypt

from config import Settings, get_settings


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Password Hashing
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


# =============================================================================
# OAuth2 Scheme
# =============================================================================

# tokenUrl is relative to the API root
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# =============================================================================
# Pydantic Models
# =============================================================================

class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: str | None = None


class User(BaseModel):
    """User model for authentication."""
    username: str


# =============================================================================
# JWT Token Functions
# =============================================================================

def create_access_token(
    data: dict,
    settings: Settings,
    expires_delta: timedelta | None = None
) -> tuple[str, int]:
    """
    Create a JWT access token.

    Returns:
        Tuple of (encoded_jwt, expires_in_seconds)
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        expires_in = settings.jwt_expire_minutes * 60

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt, expires_in


def verify_token(token: str, settings: Settings) -> TokenData:
    """
    Verify and decode a JWT token.

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        return TokenData(username=username)
    except JWTError:
        raise credentials_exception


# =============================================================================
# Authentication Functions
# =============================================================================

def authenticate_user(username: str, password: str, settings: Settings) -> User | None:
    """
    Authenticate a user with username and password.

    For this simple implementation, we check against environment variables.
    No database - single user defined in config.

    Note: API_PASSWORD environment variable must contain a bcrypt hash,
    not a plain text password. Generate with:
        python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
    """
    if username != settings.api_username:
        return None

    # Verify password against bcrypt hash stored in environment
    if not verify_password(password, settings.api_password.get_secret_value()):
        return None

    return User(username=username)


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: Annotated[User, Depends(get_current_user)]):
            return {"username": user.username}
    """
    token_data = verify_token(token, settings)

    # Verify the user still exists (matches our configured user)
    if token_data.username != settings.api_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(username=token_data.username)


# =============================================================================
# Routes
# =============================================================================

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)]
) -> Token:
    """
    OAuth2 compatible token login.

    Submit username and password to get a JWT access token.
    Use the token in the Authorization header: `Bearer <token>`
    """
    user = authenticate_user(form_data.username, form_data.password, settings)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_in = create_access_token(
        data={"sub": user.username},
        settings=settings
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )
