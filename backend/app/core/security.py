"""
Security utilities for password hashing, JWT tokens, and authentication
"""

import re
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    to_encode = {
        "exp": expire, 
        "sub": str(subject),
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return subject"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None
            
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength based on requirements
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # Check minimum length
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long")
    
    # Check for uppercase letters
    if settings.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letters
    if settings.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for numbers
    if settings.REQUIRE_NUMBERS and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    # Check for special characters
    if settings.REQUIRE_SPECIAL_CHARS and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


def generate_password_reset_token(email: str) -> str:
    """Generate password reset token"""
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "password_reset"
    }
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token and return email"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != "password_reset":
            return None
            
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None
            
        return payload.get("sub")
    except JWTError:
        return None