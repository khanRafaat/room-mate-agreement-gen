"""
Roommate Agreement Generator - Users Router
API endpoints for user management and ID verification
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.deps.auth import get_current_user, TokenData
from app.models.models import AppUser, IdVerification
from app.schemas.user import UserResponse, IdVerificationCreate, IdVerificationResponse
from app.services.kyc import kyc_service
from app.config import get_settings

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


def get_or_create_user(db: Session, token: TokenData) -> AppUser:
    """Get existing user or create a new one from token data."""
    user = db.query(AppUser).filter(AppUser.b2c_sub == token.sub).first()
    if not user:
        user = AppUser(
            b2c_sub=token.sub,
            email=token.email or f"{token.sub}@placeholder.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    user = get_or_create_user(db, current_user)
    return user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    phone: str = None,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update the current user's profile.
    """
    user = get_or_create_user(db, current_user)
    
    if phone is not None:
        user.phone = phone
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/verify", response_model=dict)
async def start_verification(
    body: IdVerificationCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Start an ID verification process.
    """
    user = get_or_create_user(db, current_user)
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified"
        )
    
    # Check for pending verification
    pending = db.query(IdVerification).filter(
        IdVerification.user_id == user.id,
        IdVerification.status == "pending"
    ).first()
    
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification already in progress"
        )
    
    if body.provider not in ["idme", "onfido", "persona"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification provider"
        )
    
    # Start verification with provider
    callback_url = f"{settings.frontend_url}/verify/callback"
    
    try:
        result = kyc_service.start_verification(
            provider=body.provider,
            user_email=user.email,
            callback_url=callback_url
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start verification: {str(e)}"
        )
    
    # Create verification record
    verification = IdVerification(
        user_id=user.id,
        provider=body.provider,
        status="pending",
        reference_id=result.get("verification_id")
    )
    db.add(verification)
    db.commit()
    
    return {
        "verification_id": str(verification.id),
        "provider": body.provider,
        "redirect_url": result.get("redirect_url")
    }


@router.get("/verify/status", response_model=List[IdVerificationResponse])
async def get_verification_status(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all ID verification records for the current user.
    """
    user = get_or_create_user(db, current_user)
    
    verifications = db.query(IdVerification).filter(
        IdVerification.user_id == user.id
    ).order_by(IdVerification.created_at.desc()).all()
    
    return verifications


@router.get("/verify/{verification_id}", response_model=IdVerificationResponse)
async def get_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a specific verification record.
    """
    user = get_or_create_user(db, current_user)
    
    from uuid import UUID
    try:
        vid = UUID(verification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification ID"
        )
    
    verification = db.query(IdVerification).filter(
        IdVerification.id == vid,
        IdVerification.user_id == user.id
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found"
        )
    
    return verification
