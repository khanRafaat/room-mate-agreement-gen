"""
Roommate Agreement Generator - Users Router
API endpoints for user management and ID verification
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.deps.auth import get_current_user, CurrentUser
from app.models.models import AppUser, IdVerification
from app.schemas.user import UserResponse, IdVerificationCreate, IdVerificationResponse, PersonaInquiryResponse
from app.services.kyc import kyc_service
from app.config import get_settings

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    return current_user.user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    phone: str = None,
    name: str = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update the current user's profile.
    """
    user = current_user.user
    
    if phone is not None:
        user.phone = phone
    if name is not None:
        user.name = name
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/verify", response_model=dict)
async def start_verification(
    body: IdVerificationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Start an ID verification process.
    """
    user = current_user.user
    
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all ID verification records for the current user.
    """
    user = current_user.user
    
    verifications = db.query(IdVerification).filter(
        IdVerification.user_id == user.id
    ).order_by(IdVerification.created_at.desc()).all()
    
    return verifications


@router.get("/verify/{verification_id}", response_model=IdVerificationResponse)
async def get_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a specific verification record.
    """
    user = current_user.user
    
    verification = db.query(IdVerification).filter(
        IdVerification.id == verification_id,
        IdVerification.user_id == user.id
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found"
        )
    
    return verification


@router.post("/verify/persona/inquiry", response_model=PersonaInquiryResponse)
async def create_persona_inquiry(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a Persona inquiry for embedded flow verification.
    
    Returns the template_id, environment_id, and reference_id needed
    to initialize the Persona SDK on the frontend.
    """
    user = current_user.user
    
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
        # Return existing inquiry info if there's a pending verification
        # User can continue the same verification
        return PersonaInquiryResponse(
            inquiry_id=pending.reference_id,
            template_id=settings.persona_template_id or "",
            environment_id=settings.persona_environment_id or "",
            reference_id=str(user.id)
        )
    
    # Validate Persona configuration
    if not settings.persona_template_id or not settings.persona_environment_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persona verification is not configured"
        )
    
    try:
        # Create inquiry using KYC service
        result = kyc_service.create_persona_inquiry(
            user_id=str(user.id),
            user_email=user.email
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Persona inquiry: {str(e)}"
        )
    
    # Create verification record
    verification = IdVerification(
        user_id=user.id,
        provider="persona",
        status="pending",
        reference_id=result.get("inquiry_id")  # May be None for SDK-created
    )
    db.add(verification)
    db.commit()
    
    return PersonaInquiryResponse(
        inquiry_id=result.get("inquiry_id"),
        template_id=result.get("template_id", ""),
        environment_id=result.get("environment_id", ""),
        reference_id=result.get("reference_id", str(user.id))
    )


@router.post("/verify/persona/complete")
async def complete_persona_verification(
    inquiry_id: str,
    status_str: str = "completed",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Called by frontend when Persona verification completes.
    Updates the verification record with the inquiry ID.
    
    Note: Actual approval happens via webhook. This just updates the inquiry_id.
    """
    user = current_user.user
    
    # Find pending verification for user
    verification = db.query(IdVerification).filter(
        IdVerification.user_id == user.id,
        IdVerification.provider == "persona",
        IdVerification.status == "pending"
    ).first()
    
    if verification:
        # Update with inquiry ID from SDK
        verification.reference_id = inquiry_id
        
        # For sandbox/testing: if status is 'completed' or 'approved', mark as approved
        # In production, this should only be done via webhook
        if status_str in ["approved", "completed"]:
            from datetime import datetime
            verification.status = "approved"
            verification.completed_at = datetime.utcnow()
            user.is_verified = True
        
        db.commit()
    
    return {"status": "updated", "inquiry_id": inquiry_id}

