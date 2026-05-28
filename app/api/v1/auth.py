import logging
import time
import hashlib
import secrets
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# Router definition
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security schemes
security_scheme = HTTPBearer(auto_error=False)

# In-memory variable to support dynamic key rotation
CURRENT_SIGNING_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

# Static user database (username -> hash of password & role)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

USERS_DB = {
    "admin": {"password_hash": hash_password("admin_password_2026"), "role": "admin"},
    "analyst": {"password_hash": hash_password("analyst_password_2026"), "role": "analyst"},
    "readonly": {"password_hash": hash_password("readonly_password_2026"), "role": "readonly"},
}

class TokenRequest(BaseModel):
    username: str = Field(..., json_schema_extra={"example": "analyst"})
    password: str = Field(..., json_schema_extra={"example": "analyst_password_2026"})

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

def create_access_token(data: dict, expires_in_seconds: int = 86400) -> str:
    """Generates a secure JWT token signed with the current key."""
    to_encode = data.copy()
    expire = int(time.time()) + expires_in_seconds
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, CURRENT_SIGNING_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token using the current signing key."""
    try:
        payload = jwt.decode(token, CURRENT_SIGNING_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        exp: Optional[int] = payload.get("exp")
        
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
            
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict[str, Any]:
    """FastAPI security dependency to validate the token and return the active user profile."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials are missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    return verify_token(token)

class RoleEnforcer:
    """Custom dependency that checks if the logged in user satisfies a role constraint."""
    def __init__(self, required_role: str):
        self.required_role = required_role
        # Mapping roles to permission tiers: admin > analyst > readonly
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
    """Exchanges valid user credentials for a secure JWT Bearer token."""
    user = USERS_DB.get(request.username)
    if not user or user["password_hash"] != hash_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate token payload
    token_data = {
        "sub": request.username,
        "role": user["role"]
    }
    access_token = create_access_token(token_data, expires_in_seconds=86400) # 24h
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest):
    """Refreshes a valid access token."""
    # To keep things secure, we decode the existing token to make sure it's valid
    user_info = verify_token(request.refresh_token)
    token_data = {
        "sub": user_info["username"],
        "role": user_info["role"]
    }
    access_token = create_access_token(token_data, expires_in_seconds=86400)
    return {"access_token": access_token, "token_type": "bearer"}

@router.put("/rotate-key")
def rotate_key(current_user: Dict[str, Any] = Depends(RoleEnforcer("admin"))):
    """Admin-only endpoint that rotates the in-memory signing key, invalidating all outstanding tokens."""
    global CURRENT_SIGNING_KEY
    CURRENT_SIGNING_KEY = secrets.token_hex(32)
    logger.warning(f"SECRET_KEY rotated by admin user '{current_user['username']}'. All existing tokens invalidated.")
    return {"message": "Key rotated successfully. All existing tokens have been invalidated."}
