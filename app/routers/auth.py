"""
Roommate Agreement Generator - Auth Router
API endpoints for user registration, login, and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AppUser
from app.schemas.auth import (
    UserRegister, UserLogin, Token, AuthResponse, 
    UserAuthResponse, PasswordChange
)
from app.services.auth import auth_service
from app.deps.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Valid email address (unique)
    - **password**: Password (min 6 characters)
    - **name**: Optional display name
    - **phone**: Optional phone number
    """
    # Check if email already exists
    existing_user = db.query(AppUser).filter(AppUser.email == body.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = auth_service.hash_password(body.password)
    
    # Create user
    user = AppUser(
        email=body.email,
        password_hash=hashed_password,
        name=body.name,
        phone=body.phone,
        b2c_sub=body.email,  # Use email as b2c_sub for local auth
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    access_token, expires_in = auth_service.create_access_token(
        user_id=str(user.id),
        email=user.email
    )
    
    return AuthResponse(
        user=UserAuthResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            is_verified=user.is_verified,
            created_at=user.created_at
        ),
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in
        )
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns a JWT access token for authenticating subsequent requests.
    """
    # Find user by email
    user = db.query(AppUser).filter(AppUser.email == body.email).first()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not auth_service.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate token
    access_token, expires_in = auth_service.create_access_token(
        user_id=str(user.id),
        email=user.email
    )
    
    return AuthResponse(
        user=UserAuthResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            is_verified=user.is_verified,
            created_at=user.created_at
        ),
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in
        )
    )


@router.get("/me", response_model=UserAuthResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    
    Requires a valid JWT token in the Authorization header.
    """
    user = current_user.user
    return UserAuthResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        phone=user.phone,
        is_verified=user.is_verified,
        created_at=user.created_at
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Refresh the JWT access token.
    
    Requires a valid (not expired) JWT token.
    """
    access_token, expires_in = auth_service.create_access_token(
        user_id=current_user.id,
        email=current_user.email
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.post("/change-password")
async def change_password(
    body: PasswordChange,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's password.
    
    Requires the current password for verification.
    """
    user = current_user.user
    
    # Verify current password
    if not user.password_hash or not auth_service.verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.password_hash = auth_service.hash_password(body.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Logout the current user.
    
    Note: JWT tokens are stateless, so this just confirms logout.
    The client should discard the token.
    """
    return {"message": "Logged out successfully"}
