"""
Roommate Agreement Generator - Invites Router
API endpoints for invite token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps.auth import get_current_user, get_current_user_optional, CurrentUser
from app.models.models import InviteToken, Agreement, AgreementParty, AppUser
from app.schemas.feedback import InviteTokenResponse, AcceptInviteRequest
from app.services.notify import notification_service
from app.config import get_settings

router = APIRouter(prefix="/invites", tags=["invites"])
settings = get_settings()


@router.get("/accept/{token}")
async def get_invite_info(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get invite information by token (public endpoint).
    
    Returns agreement info and whether user needs to register/verify.
    """
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite token"
        )
    
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has already been used"
        )
    
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired"
        )
    
    agreement = db.query(Agreement).filter(Agreement.id == invite.agreement_id).first()
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Get the initiator (owner) info
    initiator = db.query(AppUser).filter(AppUser.id == agreement.initiator_id).first()
    
    # Get the party record to check verification requirement
    party = db.query(AgreementParty).filter(
        AgreementParty.agreement_id == agreement.id,
        AgreementParty.email == invite.email
    ).first()
    
    # Check if user with this email exists and is verified
    existing_user = db.query(AppUser).filter(AppUser.email == invite.email).first()
    
    return {
        "valid": True,
        "email": invite.email,
        "agreement_id": agreement.id,
        "agreement_title": agreement.title,
        "agreement_city": agreement.city,
        "agreement_state": agreement.state,
        "owner_name": initiator.name or initiator.email if initiator else None,
        "requires_id_verification": party.requires_id_verification if party else False,
        "rent_share_cents": party.rent_share_cents if party else None,
        "expires_at": invite.expires_at,
        "user_exists": existing_user is not None,
        "user_verified": existing_user.is_verified if existing_user else False,
        "next_step": (
            "login" if existing_user and existing_user.is_verified else
            "verify" if existing_user and not existing_user.is_verified else
            "register"
        )
    }


@router.post("/accept/{token}")
async def accept_invite(
    token: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Accept an invite and join the agreement.
    
    - User must be logged in
    - User must be verified (ID.me) - unless in demo mode
    - Token must be valid and not expired
    """
    user = current_user.user
    
    # Note: Verification is checked per-party based on requires_id_verification
    # This allows tenants to accept invites without verification when owner doesn't require it
    
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite token"
        )
    
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has already been used"
        )
    
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired"
        )
    
    # Verify email matches (or allow any verified user)
    if invite.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite was sent to a different email address"
        )
    
    agreement = db.query(Agreement).filter(Agreement.id == invite.agreement_id).first()
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Find the party record for this email and link to user
    party = db.query(AgreementParty).filter(
        AgreementParty.agreement_id == agreement.id,
        AgreementParty.email == invite.email
    ).first()
    
    if party:
        # Check if ID verification is required for this party
        if party.requires_id_verification and not party.id_verified:
            # In demo mode, auto-verify; in production, require actual verification
            if settings.demo_mode:
                party.id_verified = True
            else:
                if not user.is_verified:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This agreement requires ID verification. Please complete verification first."
                    )
                party.id_verified = True
        party.user_id = user.id
    else:
        # Create new party
        party = AgreementParty(
            agreement_id=agreement.id,
            user_id=user.id,
            role="roommate",
            email=user.email,
            phone=user.phone
        )
        db.add(party)
    
    # Mark invite as used
    invite.is_used = True
    invite.used_by_user_id = user.id
    
    db.commit()
    
    return {
        "success": True,
        "message": "Successfully joined the agreement",
        "agreement_id": agreement.id
    }


@router.get("/my-invites", response_model=List[dict])
async def get_my_pending_invites(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all pending invites for the current user's email.
    """
    user = current_user.user
    
    invites = db.query(InviteToken).filter(
        InviteToken.email == user.email,
        InviteToken.is_used == False,
        InviteToken.expires_at > datetime.utcnow()
    ).all()
    
    result = []
    for invite in invites:
        agreement = db.query(Agreement).filter(Agreement.id == invite.agreement_id).first()
        initiator = db.query(AppUser).filter(AppUser.id == agreement.initiator_id).first() if agreement else None
        
        # Get the party record for this invite to check verification requirement
        party = db.query(AgreementParty).filter(
            AgreementParty.agreement_id == invite.agreement_id,
            AgreementParty.email == invite.email
        ).first()
        
        result.append({
            "token": invite.token,
            "agreement_id": invite.agreement_id,
            "agreement_title": agreement.title if agreement else None,
            "invited_by": initiator.name or initiator.email if initiator else None,
            "agreement_city": agreement.city if agreement else None,
            "agreement_state": agreement.state if agreement else None,
            "requires_id_verification": party.requires_id_verification if party else False,
            "rent_share_cents": party.rent_share_cents if party else None,
            "expires_at": invite.expires_at
        })
    
    return result


@router.delete("/{token}")
async def revoke_invite(
    token: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Revoke an invite token (only by agreement initiator).
    """
    user = current_user.user
    
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found"
        )
    
    agreement = db.query(Agreement).filter(Agreement.id == invite.agreement_id).first()
    if not agreement or agreement.initiator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the agreement initiator can revoke invites"
        )
    
    db.delete(invite)
    db.commit()
    
    return {"success": True, "message": "Invite revoked"}
