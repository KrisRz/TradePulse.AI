"""
PRODUCTION Authentication API Routes for TradePulse.AI
Real JWT tokens, bcrypt password hashing, NO DEMOS OR MOCKS
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import hashlib
import os
import secrets
import bcrypt
import jwt
from jose import JWTError

from app.backend.core.config import get_settings
from app.backend.services import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()

# PRODUCTION JWT Configuration — fail closed outside development
JWT_SECRET_KEY = settings.SECRET_KEY
if not JWT_SECRET_KEY:
    if settings.is_development:
        JWT_SECRET_KEY = "dev-only-insecure-jwt-secret"
        logger.warning("SECRET_KEY not set — using DEV-ONLY JWT secret")
    else:
        raise RuntimeError("SECRET_KEY must be set outside development")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# ---------------------------------------------------------------------------
# User store: env-seeded admin + DynamoDB-persisted registered users.
# The old in-source PRODUCTION_USERS dict (with a plaintext password in a
# comment!) is gone; registrations used to vanish on restart.
# ---------------------------------------------------------------------------
USERS_TABLE = "tradepulse-users"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@tradepulse.ai")
_ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
if not _ADMIN_PASSWORD_HASH:
    if settings.is_development:
        # dev-only seeded admin (bcrypt hash; rotate via ADMIN_PASSWORD_HASH)
        _ADMIN_PASSWORD_HASH = "$2b$12$RSfEnTeva7e9eVKvDtyFWeVcbnVhXD9iB0HweJWnfIpt30RBdGJTq"
        logger.warning("ADMIN_PASSWORD_HASH not set — DEV-ONLY seeded admin active")
    else:
        logger.error("ADMIN_PASSWORD_HASH not set — admin login DISABLED")


def _admin_user() -> Optional[Dict[str, Any]]:
    if not _ADMIN_PASSWORD_HASH:
        return None
    return {
        "password_hash": _ADMIN_PASSWORD_HASH,
        "user_id": "admin_prod_001",
        "is_admin": True,
        "username": "admin",
        "email": ADMIN_EMAIL,
        "is_active": True,
    }


def _find_user(email: str) -> Optional[Dict[str, Any]]:
    """Look up a user: env-seeded admin first, then DynamoDB (EmailIndex GSI)."""
    admin = _admin_user()
    if admin and email == admin["email"]:
        return admin
    try:
        from boto3.dynamodb.conditions import Key
        result = database_service.client.query_items(
            USERS_TABLE,
            key_condition_expression=Key("email").eq(email),
            index_name="EmailIndex",
            limit=1,
        )
        items = result.get("items") or result.get("Items") or []
        return items[0] if items else None
    except Exception as e:
        logger.error(f"User lookup failed for {email}: {e}")
        return None


def _save_user(user: Dict[str, Any]) -> bool:
    item = {**user, "id": user["user_id"]}
    return database_service.client.put_item(USERS_TABLE, item)

# Initialize database service
database_service = DatabaseService()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    email: str
    is_admin: bool
    expires_in: int

class User(BaseModel):
    user_id: str
    email: str
    username: str
    is_admin: bool = False
    is_active: bool = True

def create_production_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create production JWT token with expiration"""
    payload = {
        "user_id": user_data["user_id"],
        "email": user_data["email"],
        "is_admin": user_data["is_admin"],
        "username": user_data["username"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "iss": "tradepulse.ai",
        "sub": user_data["user_id"]
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_production_jwt_token(token: str) -> Dict[str, Any]:
    """Verify production JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.post("/login", response_model=AuthResponse)
async def production_login(request: LoginRequest) -> AuthResponse:
    """
    PRODUCTION User Login - Real JWT tokens, bcrypt passwords
    NO DEMOS, NO MOCKS, PRODUCTION READY
    """
    try:
        logger.info(f"🔐 PRODUCTION login attempt for: {request.email}")
        
        # Check user store (env-seeded admin + DynamoDB)
        user_data = _find_user(request.email)
        if user_data is None:
            logger.warning(f"❌ User not found: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password with bcrypt
        if not verify_password(request.password, user_data["password_hash"]):
            logger.warning(f"❌ Invalid password for: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user_data.get("is_active", True):
            logger.warning(f"❌ Inactive user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Generate PRODUCTION JWT token
        jwt_token = create_production_jwt_token(user_data)
        
        logger.info(f"✅ PRODUCTION login successful: {request.email} (Admin: {user_data['is_admin']})")
        
        return AuthResponse(
            access_token=jwt_token,
            token_type="bearer",
            user_id=user_data["user_id"],
            email=user_data["email"],
            is_admin=user_data["is_admin"],
            expires_in=JWT_EXPIRATION_HOURS * 3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PRODUCTION login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@router.post("/register", response_model=Dict[str, Any])
async def production_register(request: RegisterRequest) -> Dict[str, Any]:
    """
    PRODUCTION User Registration
    Real bcrypt password hashing
    """
    try:
        logger.info(f"🔐 PRODUCTION registration attempt: {request.email}")
        
        # Check if user already exists (admin seed or DynamoDB)
        if _find_user(request.email) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create new user (In AWS: store in DynamoDB)
        user_id = f"user_prod_{secrets.token_urlsafe(8)}"
        
        new_user = {
            "password_hash": password_hash,
            "user_id": user_id,
            "is_admin": False,
            "username": request.username,
            "email": request.email,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Persist in DynamoDB — registrations must survive restarts
        if not _save_user(new_user):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist user"
            )
        
        logger.info(f"✅ PRODUCTION registration successful: {request.email}")
        
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "email": request.email,
            "username": request.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PRODUCTION registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service error"
        )

@router.get("/me", response_model=User)
async def get_production_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get current user from PRODUCTION JWT token
    NO DEMO TOKEN PARSING
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token required"
            )
        
        # Verify PRODUCTION JWT token
        token_payload = verify_production_jwt_token(credentials.credentials)
        
        # Return user info from JWT payload
        return User(
            user_id=token_payload["user_id"],
            email=token_payload["email"],
            username=token_payload["username"],
            is_admin=token_payload["is_admin"],
            is_active=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.post("/logout")
async def production_logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    PRODUCTION Logout - JWT token invalidation
    """
    try:
        # In production, add token to blacklist in Redis/DynamoDB
        # For now, just verify token is valid
        if credentials:
            verify_production_jwt_token(credentials.credentials)
        
        logger.info("✅ PRODUCTION logout successful")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.warning(f"⚠️ Logout warning: {e}")
        # Even if token is invalid, logout should succeed
        return {"message": "Logout completed"}

@router.get("/health")
async def auth_health():
    """Auth service health check"""
    return {
        "service": "production_auth",
        "status": "operational",
        "jwt_algorithm": JWT_ALGORITHM,
        "token_expiration_hours": JWT_EXPIRATION_HOURS,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }