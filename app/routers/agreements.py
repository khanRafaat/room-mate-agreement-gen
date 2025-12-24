"""
Roommate Agreement Generator - Agreements Router
API endpoints for agreement management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps.auth import get_current_user, TokenData
from app.models.models import (
    AppUser, Agreement, AgreementParty, AgreementTerms, Payment
)
from app.schemas.agreement import (
    AgreementCreate, AgreementResponse, AgreementListResponse,
    AgreementUpdate, InviteRequest, AgreementPartyResponse
)
from app.schemas.payment import CheckoutLinks, CheckoutResponse
from app.services.payments import payments_service
from app.services.notify import notification_service
from app.services.docusign import docusign_service
from app.config import get_settings

router = APIRouter(prefix="/agreements", tags=["agreements"])
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


@router.post("", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_agreement(
    body: AgreementCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new roommate agreement (draft status, awaiting payment).
    """
    user = get_or_create_user(db, current_user)
    
    # Create agreement
    agreement = Agreement(
        initiator_id=user.id,
        title=body.title,
        address_line1=body.address_line1,
        address_line2=body.address_line2,
        city=body.city,
        state=body.state,
        postal_code=body.postal_code,
        country=body.country,
        start_date=body.start_date,
        end_date=body.end_date,
        rent_total_cents=body.rent_total_cents,
        status="awaiting_payment"
    )
    db.add(agreement)
    db.flush()
    
    # Add initiator as a party
    initiator_party = AgreementParty(
        agreement_id=agreement.id,
        user_id=user.id,
        role="initiator",
        email=user.email,
        phone=user.phone
    )
    db.add(initiator_party)
    
    # Add terms if provided
    if body.terms:
        terms = AgreementTerms(
            agreement_id=agreement.id,
            quiet_hours=body.terms.quiet_hours.model_dump() if body.terms.quiet_hours else None,
            guest_rules=body.terms.guest_rules.model_dump() if body.terms.guest_rules else None,
            pet_rules=body.terms.pet_rules.model_dump() if body.terms.pet_rules else None,
            deposit_cents=body.terms.deposit_cents,
            deposit_forfeit_reasons=body.terms.deposit_forfeit_reasons,
            additional_rules=body.terms.additional_rules,
            no_offensive_clause_ack=body.terms.no_offensive_clause_ack
        )
        db.add(terms)
    
    # Add roommate parties if provided
    if body.parties:
        for party_data in body.parties:
            party = AgreementParty(
                agreement_id=agreement.id,
                role=party_data.role,
                email=party_data.email,
                phone=party_data.phone,
                rent_share_cents=party_data.rent_share_cents,
                utilities=party_data.utilities,
                chores=party_data.chores
            )
            db.add(party)
    
    db.commit()
    db.refresh(agreement)
    
    return agreement


@router.get("", response_model=List[AgreementListResponse])
async def list_agreements(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    List all agreements for the current user.
    """
    user = get_or_create_user(db, current_user)
    
    # Get agreements where user is initiator or a party
    agreements = db.query(Agreement).filter(
        (Agreement.initiator_id == user.id) |
        (Agreement.parties.any(AgreementParty.user_id == user.id))
    ).order_by(Agreement.created_at.desc()).all()
    
    return agreements


@router.get("/{agreement_id}", response_model=AgreementResponse)
async def get_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a specific agreement by ID.
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(Agreement.id == agreement_id).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check user has access (is initiator or a party)
    is_party = any(p.user_id == user.id or p.email == user.email for p in agreement.parties)
    if agreement.initiator_id != user.id and not is_party:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agreement"
        )
    
    return agreement


@router.patch("/{agreement_id}", response_model=AgreementResponse)
async def update_agreement(
    agreement_id: UUID,
    body: AgreementUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update an agreement (only allowed in draft/awaiting_payment status).
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == agreement_id,
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status not in ["draft", "awaiting_payment"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update agreement after payment"
        )
    
    # Update fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agreement, field, value)
    
    db.commit()
    db.refresh(agreement)
    
    return agreement


@router.post("/{agreement_id}/pay", response_model=CheckoutLinks)
async def initiate_payment(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get payment checkout links (card and crypto options).
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == agreement_id,
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status not in ["draft", "awaiting_payment"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement already paid or in signing process"
        )
    
    agreement_id_str = str(agreement.id)
    
    # Create checkout sessions
    card_checkout = None
    crypto_checkout = None
    
    try:
        card_result = payments_service.start_card_checkout(agreement_id_str)
        
        # Create pending payment record
        card_payment = Payment(
            agreement_id=agreement.id,
            method="card",
            amount_cents=settings.stripe_price_cents,
            status="pending",
            provider_ref=card_result["session_id"]
        )
        db.add(card_payment)
        db.flush()
        
        card_checkout = CheckoutResponse(
            payment_id=card_payment.id,
            method="card",
            checkout_url=card_result["url"]
        )
    except Exception:
        pass  # Card payment not configured
    
    try:
        crypto_result = payments_service.start_crypto_checkout(agreement_id_str)
        
        # Create pending payment record
        crypto_payment = Payment(
            agreement_id=agreement.id,
            method="solana",
            amount_cents=200,  # $2.00
            status="pending",
            provider_ref=crypto_result["charge_id"]
        )
        db.add(crypto_payment)
        db.flush()
        
        crypto_checkout = CheckoutResponse(
            payment_id=crypto_payment.id,
            method="solana",
            checkout_url=crypto_result["url"]
        )
    except Exception:
        pass  # Crypto payment not configured
    
    db.commit()
    
    return CheckoutLinks(card=card_checkout, crypto=crypto_checkout)


@router.post("/{agreement_id}/invite", response_model=dict)
async def invite_roommates(
    agreement_id: UUID,
    body: InviteRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Invite roommates to the agreement (requires payment first).
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == agreement_id,
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check payment status
    successful_payment = db.query(Payment).filter(
        Payment.agreement_id == agreement.id,
        Payment.status == "succeeded"
    ).first()
    
    if not successful_payment and agreement.status == "awaiting_payment":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required before inviting roommates"
        )
    
    # Add roommates and send invites
    invited_count = 0
    for roommate in body.roommates:
        # Check if already a party
        existing = db.query(AgreementParty).filter(
            AgreementParty.agreement_id == agreement.id,
            AgreementParty.email == roommate.email
        ).first()
        
        if not existing:
            party = AgreementParty(
                agreement_id=agreement.id,
                role="roommate",
                email=roommate.email,
                phone=roommate.phone,
                rent_share_cents=roommate.rent_share_cents,
                utilities=roommate.utilities,
                chores=roommate.chores
            )
            db.add(party)
            
            # Send invite email
            try:
                invite_link = f"{settings.frontend_url}/agreements/{agreement.id}/join"
                notification_service.send_invite_email(
                    to_email=roommate.email,
                    inviter_name=user.email,
                    agreement_title=agreement.title,
                    invite_link=invite_link
                )
            except Exception:
                pass  # Email not configured
            
            invited_count += 1
    
    # Update agreement status
    agreement.status = "inviting"
    db.commit()
    
    return {"ok": True, "invited_count": invited_count}


@router.post("/{agreement_id}/docusign/envelope", response_model=dict)
async def create_docusign_envelope(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a DocuSign envelope for the agreement.
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == agreement_id,
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status not in ["inviting", "signing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement not ready for signing"
        )
    
    # TODO: Generate PDF from template
    # For now, return a placeholder response
    
    return {
        "ok": True,
        "message": "DocuSign envelope creation requires PDF template generation",
        "agreement_id": str(agreement.id)
    }


@router.get("/{agreement_id}/signlink", response_model=dict)
async def get_signing_link(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get embedded signing link for the current user.
    """
    user = get_or_create_user(db, current_user)
    
    agreement = db.query(Agreement).filter(Agreement.id == agreement_id).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check user is a party
    party = next(
        (p for p in agreement.parties if p.user_id == user.id or p.email == user.email),
        None
    )
    
    if not party:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a party to this agreement"
        )
    
    if party.signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already signed this agreement"
        )
    
    # TODO: Get actual signing link from DocuSign envelope
    
    return {
        "ok": True,
        "message": "Signing link requires active DocuSign envelope",
        "agreement_id": str(agreement.id)
    }
