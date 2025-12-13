"""
JWT Authentication and Authorization
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging

from shared.config import get_settings
from shared.redis_client import get_redis, RedisClient

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token
security = HTTPBearer()


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication"""
    id: str
    email: str
    is_active: bool = True
    is_superuser: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


async def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        scopes: list = payload.get("scopes", [])
        
        if user_id is None:
            raise credentials_exception
        
        token_data = TokenData(
            user_id=user_id,
            email=email,
            scopes=scopes
        )
        return token_data
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: RedisClient = Depends(get_redis)
) -> User:
    """
    Get current authenticated user from JWT token
    Dependency for protected routes
    """
    token = credentials.credentials
    
    # Check if token is blacklisted
    is_blacklisted = await redis.exists(f"blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Decode token
    token_data = await decode_token(token)
    
    # Check if user exists in cache
    user_cache_key = f"user:{token_data.user_id}"
    cached_user = await redis.get(user_cache_key)
    
    if cached_user:
        return User(**cached_user)
    
    # In production, fetch from database
    # For now, create user from token data
    user = User(
        id=token_data.user_id,
        email=token_data.email or "",
        is_active=True
    )
    
    # Cache user for 5 minutes
    await redis.set(user_cache_key, user.dict(), expire=300)
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is superuser (admin)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def revoke_token(
    token: str,
    redis: RedisClient = Depends(get_redis)
):
    """Revoke a token (add to blacklist)"""
    try:
        # Decode to get expiration
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        exp = payload.get("exp")
        if exp:
            # Calculate TTL (time until token expires)
            exp_datetime = datetime.fromtimestamp(exp)
            ttl = int((exp_datetime - datetime.utcnow()).total_seconds())
            
            if ttl > 0:
                # Add to blacklist with TTL
                await redis.set(f"blacklist:{token}", "1", expire=ttl)
                logger.info(f"Token revoked successfully")
                
    except JWTError as e:
        logger.error(f"Error revoking token: {e}")


# Optional: API Key authentication for service-to-service communication
async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Verify API key for service-to-service auth"""
    api_key = credentials.credentials
    
    # In production, verify against database
    # For now, check against environment variable
    valid_api_key = settings.DJANGO_API_KEY
    
    if api_key != valid_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True
