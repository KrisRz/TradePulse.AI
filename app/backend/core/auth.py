"""
Professional Authentication System for TradePulse.AI

Enterprise-grade JWT authentication with:
- Access and refresh token management
- Token rotation and blacklisting
- Role-based access control
- Session management
- Security best practices
"""

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass
from uuid import uuid4
import structlog
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .environments import get_config
from .exceptions import (
    AuthenticationException,
    AuthorizationException,
    TokenExpiredException
)

logger = structlog.get_logger(__name__)


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_USER = "api_user"


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenPayload:
    """JWT token payload structure"""
    user_id: str
    email: str
    roles: List[UserRole]
    token_type: TokenType
    session_id: str
    issued_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JWT encoding"""
        return {
            "sub": self.user_id,
            "email": self.email,
            "roles": [role.value for role in self.roles],
            "token_type": self.token_type.value,
            "session_id": self.session_id,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "jti": str(uuid4())  # JWT ID for blacklisting
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create from JWT payload dictionary"""
        return cls(
            user_id=data["sub"],
            email=data["email"],
            roles=[UserRole(role) for role in data["roles"]],
            token_type=TokenType(data["token_type"]),
            session_id=data["session_id"],
            issued_at=datetime.fromtimestamp(data["iat"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(data["exp"], tz=timezone.utc)
        )


class TokenPair(BaseModel):
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds


class User(BaseModel):
    """User model"""
    id: str
    email: str
    roles: List[UserRole]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthenticationManager:
    """Professional authentication manager"""
    
    def __init__(self):
        self.config = get_config()
        self.security_config = self.config.security
        self.secret_key = self.security_config.secret_key.get_secret_value()
        self.algorithm = self.security_config.algorithm
        
        # Token blacklist (in production, use Redis or database)
        self.blacklisted_tokens: set = set()
        
        # Active sessions (in production, use Redis)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def create_token_pair(
        self,
        user: User,
        session_id: Optional[str] = None
    ) -> TokenPair:
        """Create access and refresh token pair"""
        
        if not session_id:
            session_id = str(uuid4())
        
        now = datetime.now(timezone.utc)
        
        # Create access token
        access_expires = now + timedelta(
            minutes=self.security_config.access_token_expire_minutes
        )
        access_payload = TokenPayload(
            user_id=user.id,
            email=user.email,
            roles=user.roles,
            token_type=TokenType.ACCESS,
            session_id=session_id,
            issued_at=now,
            expires_at=access_expires
        )
        
        # Create refresh token
        refresh_expires = now + timedelta(
            days=self.security_config.refresh_token_expire_days
        )
        refresh_payload = TokenPayload(
            user_id=user.id,
            email=user.email,
            roles=user.roles,
            token_type=TokenType.REFRESH,
            session_id=session_id,
            issued_at=now,
            expires_at=refresh_expires
        )
        
        # Encode tokens
        access_token = jwt.encode(
            access_payload.to_dict(),
            self.secret_key,
            algorithm=self.algorithm
        )
        
        refresh_token = jwt.encode(
            refresh_payload.to_dict(),
            self.secret_key,
            algorithm=self.algorithm
        )
        
        # Store session
        self.active_sessions[session_id] = {
            "user_id": user.id,
            "created_at": now,
            "last_activity": now,
            "refresh_token_jti": refresh_payload.to_dict()["jti"]
        }
        
        logger.info(
            "Token pair created",
            user_id=user.id,
            session_id=session_id,
            access_expires=access_expires,
            refresh_expires=refresh_expires
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.security_config.access_token_expire_minutes * 60
        )
    
    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti in self.blacklisted_tokens:
                raise AuthenticationException("Token has been revoked")
            
            return TokenPayload.from_dict(payload)
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredException()
        except jwt.InvalidTokenError as e:
            raise AuthenticationException(f"Invalid token: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Refresh access token using refresh token"""
        
        # Decode refresh token
        payload = self.decode_token(refresh_token)
        
        if payload.token_type != TokenType.REFRESH:
            raise AuthenticationException("Invalid token type for refresh")
        
        # Check if session is still active
        session = self.active_sessions.get(payload.session_id)
        if not session:
            raise AuthenticationException("Session not found or expired")
        
        # Create new token pair (token rotation)
        user = User(
            id=payload.user_id,
            email=payload.email,
            roles=payload.roles,
            created_at=datetime.now(timezone.utc)  # This would come from database
        )
        
        # Blacklist old refresh token
        old_jti = session.get("refresh_token_jti")
        if old_jti:
            self.blacklisted_tokens.add(old_jti)
        
        # Create new token pair
        new_tokens = self.create_token_pair(user, payload.session_id)
        
        logger.info(
            "Access token refreshed",
            user_id=payload.user_id,
            session_id=payload.session_id
        )
        
        return new_tokens
    
    def revoke_token(self, token: str) -> None:
        """Revoke a token (add to blacklist)"""
        try:
            payload = self.decode_token(token)
            jti = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't verify expiry for revocation
            ).get("jti")
            
            if jti:
                self.blacklisted_tokens.add(jti)
                
            logger.info(
                "Token revoked",
                user_id=payload.user_id,
                token_type=payload.token_type.value
            )
                
        except Exception as e:
            logger.warning(f"Failed to revoke token: {e}")
    
    def revoke_session(self, session_id: str) -> None:
        """Revoke entire session"""
        session = self.active_sessions.get(session_id)
        if session:
            # Blacklist refresh token
            refresh_jti = session.get("refresh_token_jti")
            if refresh_jti:
                self.blacklisted_tokens.add(refresh_jti)
            
            # Remove session
            del self.active_sessions[session_id]
            
            logger.info("Session revoked", session_id=session_id)
    
    def cleanup_expired_tokens(self) -> None:
        """Clean up expired tokens and sessions"""
        now = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            # Check if session is too old (beyond refresh token expiry)
            created_at = session_data["created_at"]
            max_age = timedelta(days=self.security_config.refresh_token_expire_days)
            
            if now - created_at > max_age:
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            self.revoke_session(session_id)
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Global authentication manager
_auth_manager: Optional[AuthenticationManager] = None

def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager


# FastAPI dependencies
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """FastAPI dependency to get current authenticated user"""
    
    auth_manager = get_auth_manager()
    
    try:
        payload = auth_manager.decode_token(credentials.credentials)
        
        if payload.token_type != TokenType.ACCESS:
            raise AuthenticationException("Invalid token type")
        
        # In production, fetch user from database
        user = User(
            id=payload.user_id,
            email=payload.email,
            roles=payload.roles,
            created_at=datetime.now(timezone.utc)
        )
        
        return user
        
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*required_roles: UserRole):
    """Decorator to require specific roles"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Convenience dependencies
require_admin = require_roles(UserRole.ADMIN)
require_trader = require_roles(UserRole.TRADER, UserRole.ADMIN)
require_viewer = require_roles(UserRole.VIEWER, UserRole.TRADER, UserRole.ADMIN)

