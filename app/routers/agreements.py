"""
Roommate Agreement Generator - Agreements Router
API endpoints for agreement management with verification enforcement
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.deps.auth import get_current_user, CurrentUser
from app.models.models import (
    AppUser, Agreement, AgreementParty, AgreementTerms, Payment, InviteToken
)
from app.schemas.agreement import (
    AgreementCreate, AgreementResponse, AgreementListResponse,
    AgreementUpdate, InviteRequest, AgreementPartyResponse
)
from app.schemas.payment import CheckoutLinks, CheckoutResponse
from app.schemas.feedback import InviteTokenResponse
from app.services.payments import payments_service
from app.services.notify import notification_service
from app.services.docusign import docusign_service
from app.config import get_settings

router = APIRouter(prefix="/agreements", tags=["agreements"])
settings = get_settings()


def require_verified_user(user: AppUser):
    """Check that user is ID verified, raise exception if not."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must complete ID verification (ID.me) before creating or viewing agreements"
        )


@router.post("", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_agreement(
    body: AgreementCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new roommate agreement (draft status).
    
    **Requires**: User must be ID verified via ID.me
    
    Agreement starts as 'draft' and moves to 'awaiting_payment' when ready.
    """
    user = current_user.user
    
    # Enforce ID verification
    require_verified_user(user)
    
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
        status="draft"  # Start as draft, not awaiting_payment
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
    
    # Add roommate parties if provided (as placeholders)
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    List all agreements for the current user.
    """
    user = current_user.user
    
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a specific agreement by ID.
    
    **Requires**: User must be ID verified to view agreement details.
    """
    user = current_user.user
    
    # Enforce ID verification for viewing
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(Agreement.id == str(agreement_id)).first()
    
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update an agreement (only allowed in draft status).
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status not in ["draft"]:
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


@router.post("/{agreement_id}/finalize", response_model=dict)
async def finalize_draft(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Finalize a draft agreement and move it to awaiting_payment status.
    
    This step is required before payment.
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement is not in draft status"
        )
    
    # Move to awaiting_payment
    agreement.status = "awaiting_payment"
    db.commit()
    
    return {"ok": True, "status": "awaiting_payment", "message": "Agreement finalized. Please complete payment."}


@router.post("/{agreement_id}/pay", response_model=CheckoutLinks)
async def initiate_payment(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get payment checkout links (card and crypto options).
    
    Only available after agreement is finalized (awaiting_payment status).
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status != "awaiting_payment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement must be finalized before payment"
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


@router.post("/{agreement_id}/invite", response_model=List[InviteTokenResponse])
async def invite_roommates(
    agreement_id: UUID,
    body: InviteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Invite roommates to the agreement via email.
    
    **Requires**: Agreement must be paid (status = 'paid')
    
    Generates unique invite tokens and sends email invitations.
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check payment status - must be paid
    if agreement.status not in ["paid", "inviting"]:
        successful_payment = db.query(Payment).filter(
            Payment.agreement_id == agreement.id,
            Payment.status == "succeeded"
        ).first()
        
        if not successful_payment:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Payment required before inviting roommates"
            )
        
        # Update status to paid
        agreement.status = "paid"
    
    # Generate invites
    invite_responses = []
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    for roommate in body.roommates:
        # Check if already a party with user_id
        existing_party = db.query(AgreementParty).filter(
            AgreementParty.agreement_id == agreement.id,
            AgreementParty.email == roommate.email,
            AgreementParty.user_id != None
        ).first()
        
        if existing_party:
            continue  # Already joined
        
        # Check for existing unused invite
        existing_invite = db.query(InviteToken).filter(
            InviteToken.agreement_id == agreement.id,
            InviteToken.email == roommate.email,
            InviteToken.is_used == False
        ).first()
        
        if existing_invite:
            # Update expiry
            existing_invite.expires_at = expires_at
            invite_token = existing_invite
        else:
            # Create party placeholder if not exists
            party = db.query(AgreementParty).filter(
                AgreementParty.agreement_id == agreement.id,
                AgreementParty.email == roommate.email
            ).first()
            
            if not party:
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
            
            # Create invite token
            invite_token = InviteToken(
                agreement_id=agreement.id,
                email=roommate.email,
                expires_at=expires_at
            )
            db.add(invite_token)
            db.flush()
        
        invite_url = f"{settings.frontend_url}/invites/accept/{invite_token.token}"
        
        # Send invite email
        try:
            notification_service.send_invite_email(
                to_email=roommate.email,
                inviter_name=user.name or user.email,
                agreement_title=agreement.title,
                invite_link=invite_url
            )
        except Exception:
            pass  # Email not configured
        
        invite_responses.append(InviteTokenResponse(
            token=invite_token.token,
            email=invite_token.email,
            expires_at=invite_token.expires_at,
            invite_url=invite_url
        ))
    
    # Update agreement status
    agreement.status = "inviting"
    db.commit()
    
    return invite_responses


@router.post("/{agreement_id}/docusign/envelope", response_model=dict)
async def create_docusign_envelope(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a DocuSign envelope for the agreement.
    
    All parties must have joined before creating the envelope.
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
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
    
    # Check all parties have joined (have user_id)
    unjoined = [p for p in agreement.parties if p.user_id is None]
    if unjoined:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waiting for {len(unjoined)} roommate(s) to join before signing"
        )
    
    # Update status
    agreement.status = "signing"
    db.commit()
    
    # TODO: Generate PDF and create DocuSign envelope
    
    return {
        "ok": True,
        "message": "Agreement ready for signing. DocuSign envelope creation requires PDF template.",
        "agreement_id": str(agreement.id),
        "status": "signing"
    }


@router.get("/{agreement_id}/signlink", response_model=dict)
async def get_signing_link(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get embedded signing link for the current user.
    
    User must be a verified party of the agreement.
    """
    user = current_user.user
    require_verified_user(user)
    
    agreement = db.query(Agreement).filter(Agreement.id == str(agreement_id)).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check user is a party
    party = next(
        (p for p in agreement.parties if p.user_id == user.id),
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


@router.post("/{agreement_id}/complete", response_model=dict)
async def complete_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Mark agreement as completed (all signatures received).
    
    In production, this would be triggered by DocuSign webhook.
    """
    user = current_user.user
    
    agreement = db.query(Agreement).filter(
        Agreement.id == str(agreement_id),
        Agreement.initiator_id == user.id
    ).first()
    
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check all parties have signed
    unsigned = [p for p in agreement.parties if not p.signed]
    if unsigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waiting for {len(unsigned)} signature(s)"
        )
    
    agreement.status = "completed"
    db.commit()
    
    return {"ok": True, "status": "completed", "message": "Agreement completed!"}
