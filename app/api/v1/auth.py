import logging
import os
import time
import hashlib
import secrets
import uuid
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import settings
from app.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Router definition
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security schemes
security_scheme = HTTPBearer(auto_error=False)

# In-memory variable to support dynamic key rotation
CURRENT_SIGNING_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

# Token TTL constants (in seconds)
ACCESS_TOKEN_EXPIRE_SECONDS = 1800    # 30 minutes
REFRESH_TOKEN_EXPIRE_SECONDS = 604800  # 7 days

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _build_users_db() -> dict:
    """Loads user credentials from environment variables only. Never from source."""
    users = {}
    for role in ["admin", "analyst", "readonly"]:
        username_key = f"ARTHA_{role.upper()}_USERNAME"
        password_key = f"ARTHA_{role.upper()}_PASSWORD"
        username = os.getenv(username_key)
        password = os.getenv(password_key)
        if username and password:
            users[username] = {
                "password_hash": hash_password(password),
                "role": role
            }
        else:
            logger.warning(f"Credentials for role '{role}' not set in environment.")
            
    if not users:
        if settings.ENV != "production":
            logger.info("Local environment detected. Populating USERS_DB from settings defaults.")
            return {
                settings.ADMIN_USERNAME: {"password_hash": hash_password(settings.ADMIN_PASSWORD), "role": "admin"},
                settings.ANALYST_USERNAME: {"password_hash": hash_password(settings.ANALYST_PASSWORD), "role": "analyst"},
                settings.READONLY_USERNAME: {"password_hash": hash_password(settings.READONLY_PASSWORD), "role": "readonly"},
            }
        raise RuntimeError(
            "STARTUP FAILURE: No user credentials configured. "
            "Set ARTHA_ADMIN_USERNAME, ARTHA_ADMIN_PASSWORD, etc. in environment."
        )
    return users

USERS_DB = _build_users_db()

# ==========================================
# Redis JTI Blacklisting & Revocation
# ==========================================

def blacklist_jti(jti: str, exp_timestamp: float) -> bool:
    """Blacklists a JWT ID (JTI) in Redis until its expiration timestamp."""
    remaining_ttl = int(exp_timestamp - time.time())
    if remaining_ttl <= 0:
        return True  # Already expired, no need to store
    try:
        redis_client = get_redis_client()
        key = f"auth:blacklist:{jti}"
        redis_client.set(key, "revoked", ex=remaining_ttl)
        logger.info(f"JTI '{jti}' successfully blacklisted in Redis (TTL: {remaining_ttl}s).")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist JTI '{jti}' in Redis: {e}")
        return False

def is_jti_blacklisted(jti: str) -> bool:
    """Checks if a JTI has been revoked/blacklisted in Redis."""
    if not jti:
        return False
    try:
        redis_client = get_redis_client()
        key = f"auth:blacklist:{jti}"
        val = redis_client.get(key)
        return val == "revoked" or val == b"revoked"
    except Exception as e:
        logger.error(f"Failed checking JTI revocation status for '{jti}': {e}")
        return False

# ==========================================
# Dual-Token Generation & Verification
# ==========================================

class TokenRequest(BaseModel):
    username: str = Field(..., json_schema_extra={"example": "analyst"})
    password: str = Field(..., json_schema_extra={"example": "analyst_password_2026"})

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS
    refresh_expires_in: int = REFRESH_TOKEN_EXPIRE_SECONDS

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class RevokeRequest(BaseModel):
    jti: str

def create_access_token(data: dict, expires_in_seconds: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    """Generates a secure access JWT token with a unique JTI."""
    to_encode = data.copy()
    now = int(time.time())
    expire = now + expires_in_seconds
    token_jti = to_encode.get("jti") or str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": token_jti,
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, CURRENT_SIGNING_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_in_seconds: int = REFRESH_TOKEN_EXPIRE_SECONDS) -> str:
    """Generates a long-lived refresh JWT token with a unique JTI."""
    to_encode = data.copy()
    now = int(time.time())
    expire = now + expires_in_seconds
    token_jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": token_jti,
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, CURRENT_SIGNING_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_token_pair(data: dict) -> Dict[str, Any]:
    """Creates a dual-token pair (access + refresh) for authentication."""
    access_token = create_access_token(data, expires_in_seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    refresh_token = create_refresh_token(data, expires_in_seconds=REFRESH_TOKEN_EXPIRE_SECONDS)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "refresh_expires_in": REFRESH_TOKEN_EXPIRE_SECONDS
    }

def verify_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Decodes and validates a JWT token, enforcing Redis JTI revocation blacklisting."""
    try:
        payload = jwt.decode(token, CURRENT_SIGNING_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        exp: Optional[float] = payload.get("exp")
        jti: Optional[str] = payload.get("jti")
        token_type: Optional[str] = payload.get("type")
        
        if not username or not role or not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing required attributes.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if exp < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if expected_type and token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected '{expected_type}', got '{token_type}'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Enforce Redis JTI revocation blacklist check
        if jti and is_jti_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return {"username": username, "role": role, "jti": jti, "exp": exp, "type": token_type}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict[str, Any]:
    """FastAPI security dependency to validate the access token and return the active user profile."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials are missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    user_data = verify_token(token, expected_type="access")
    return user_data

class RoleEnforcer:
    """Custom dependency that checks if the logged in user satisfies a role constraint."""
    def __init__(self, required_role: str):
        self.required_role = required_role
        self.role_hierarchy = {"admin": 3, "analyst": 2, "readonly": 1}

    def __call__(self, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "readonly")
        user_tier = self.role_hierarchy.get(user_role, 1)
        required_tier = self.role_hierarchy.get(self.required_role, 1)
        
        if user_tier < required_tier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires role '{self.required_role}' or higher. Current role: '{user_role}'"
            )
        return current_user

# ==========================================
# API Routes
# ==========================================

@router.post("/token", response_model=TokenResponse)
def login_for_access_token(request: TokenRequest):
    """Exchanges valid user credentials for an Enterprise Dual-Token Pair (Access + Refresh)."""
    user = USERS_DB.get(request.username)
    if not user or user["password_hash"] != hash_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token_payload = {
        "sub": request.username,
        "role": user["role"]
    }
    return create_token_pair(token_payload)

@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(request: RefreshRequest):
    """Exchanges a valid refresh token for a new Dual-Token Pair, blacklisting the old refresh token JTI."""
    # 1. Verify that the refresh token is valid, unexpired, and not revoked
    token_info = verify_token(request.refresh_token, expected_type="refresh")
    
    # 2. Enforce Single-Use Rotation: Blacklist the used refresh token JTI
    if token_info.get("jti") and token_info.get("exp"):
        blacklist_jti(token_info["jti"], token_info["exp"])

    # 3. Issue new Dual-Token pair
    token_payload = {
        "sub": token_info["username"],
        "role": token_info["role"]
    }
    return create_token_pair(token_payload)

@router.post("/logout")
def logout(
    request: Optional[LogoutRequest] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
):
    """Revokes the current access token and optional refresh token in Redis."""
    revoked_count = 0
    if credentials:
        try:
            token_info = verify_token(credentials.credentials)
            if token_info.get("jti") and token_info.get("exp"):
                blacklist_jti(token_info["jti"], token_info["exp"])
                revoked_count += 1
        except HTTPException:
            pass  # Token might already be expired or invalid

    if request and request.refresh_token:
        try:
            refresh_info = verify_token(request.refresh_token, expected_type="refresh")
            if refresh_info.get("jti") and refresh_info.get("exp"):
                blacklist_jti(refresh_info["jti"], refresh_info["exp"])
                revoked_count += 1
        except HTTPException:
            pass

    return {
        "message": f"Logout successful. Revoked {revoked_count} token(s).",
        "revoked_count": revoked_count
    }

@router.post("/revoke")
def revoke_jti(
    request: RevokeRequest,
    current_user: Dict[str, Any] = Depends(RoleEnforcer("admin"))
):
    """Admin-only endpoint to manually revoke any JWT by its JTI."""
    exp_time = time.time() + 86400  # Default 24h blacklist TTL if unknown
    success = blacklist_jti(request.jti, exp_time)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke JTI in Redis."
        )
    return {"message": f"JTI '{request.jti}' has been revoked.", "jti": request.jti}

@router.put("/rotate-key")
def rotate_key(current_user: Dict[str, Any] = Depends(RoleEnforcer("admin"))):
    """Admin-only endpoint that rotates the in-memory signing key, invalidating all outstanding tokens."""
    global CURRENT_SIGNING_KEY
    CURRENT_SIGNING_KEY = secrets.token_hex(32)
    logger.warning(f"SECRET_KEY rotated by admin user '{current_user['username']}'. All existing tokens invalidated.")
    return {"message": "Key rotated successfully. All existing tokens have been invalidated."}
