"""
Roommate Agreement Generator - Authentication Dependencies
JWT token validation and user extraction (local auth)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.services.auth import auth_service
from app.models.models import AppUser

settings = get_settings()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Authenticated user data."""
    
    def __init__(self, user: AppUser):
        self.id = str(user.id)
        self.email = user.email
        self.name = user.name
        self.phone = user.phone
        self.is_verified = user.is_verified
        self.user = user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    Validates JWT token and returns user from database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    payload = auth_service.decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return CurrentUser(user)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no token provided or invalid.
    """
    if credentials is None:
        return None
    
    try:
        payload = auth_service.decode_token(credentials.credentials)
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(AppUser).filter(AppUser.id == user_id).first()
        if user is None:
            return None
        
        return CurrentUser(user)
    except Exception:
        return None


# Dependency for protected routes
auth_dependency = Depends(get_current_user)
