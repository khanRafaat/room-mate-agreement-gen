"""
Roommate Agreement Generator - Webhooks Router
Webhook endpoints for Stripe, Coinbase, and DocuSign
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.models import Agreement, Payment, SignatureEnvelope, AgreementParty
from app.services.payments import payments_service
from app.services.notify import notification_service
from app.config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events (payment completion, etc.).
    """
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    try:
        event = payments_service.verify_stripe_webhook(payload, signature)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook: {str(e)}"
        )
    
    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        agreement_id = session.get("metadata", {}).get("agreement_id")
        
        if agreement_id:
            # Update payment status
            payment = db.query(Payment).filter(
                Payment.provider_ref == session["id"]
            ).first()
            
            if payment:
                payment.status = "succeeded"
                
                # Update agreement status
                agreement = db.query(Agreement).filter(
                    Agreement.id == payment.agreement_id
                ).first()
                
                if agreement and agreement.status == "awaiting_payment":
                    agreement.status = "inviting"
                
                db.commit()
    
    # Handle payment_intent.payment_failed
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        
        # Find and update payment
        payment = db.query(Payment).filter(
            Payment.provider_ref == payment_intent.get("id")
        ).first()
        
        if payment:
            payment.status = "failed"
            db.commit()
    
    return {"received": True}


@router.post("/coinbase")
async def coinbase_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Coinbase Commerce webhook events.
    """
    payload = await request.body()
    signature = request.headers.get("X-CC-Webhook-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Coinbase signature"
        )
    
    try:
        if not payments_service.verify_coinbase_webhook(payload, signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    data = json.loads(payload)
    event = data.get("event", {})
    event_type = event.get("type")
    charge = event.get("data", {})
    
    charge_id = charge.get("id")
    agreement_id = charge.get("metadata", {}).get("agreement_id")
    
    if not charge_id:
        return {"received": True}
    
    # Find payment by charge ID
    payment = db.query(Payment).filter(
        Payment.provider_ref == charge_id
    ).first()
    
    if not payment:
        return {"received": True}
    
    # Handle different event types
    if event_type == "charge:confirmed":
        payment.status = "succeeded"
        
        # Update agreement status
        agreement = db.query(Agreement).filter(
            Agreement.id == payment.agreement_id
        ).first()
        
        if agreement and agreement.status == "awaiting_payment":
            agreement.status = "inviting"
        
        db.commit()
    
    elif event_type == "charge:failed":
        payment.status = "failed"
        db.commit()
    
    elif event_type == "charge:pending":
        payment.status = "pending"
        db.commit()
    
    return {"received": True}


@router.post("/docusign")
async def docusign_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle DocuSign Connect webhook events (envelope status changes).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # DocuSign Connect sends envelope status updates
    envelope_id = payload.get("envelopeId")
    envelope_status = payload.get("status")
    
    if not envelope_id:
        return {"received": True}
    
    # Find envelope record
    envelope = db.query(SignatureEnvelope).filter(
        SignatureEnvelope.docusign_envelope_id == envelope_id
    ).first()
    
    if not envelope:
        return {"received": True}
    
    # Update envelope status
    envelope.status = envelope_status
    
    # Handle completed envelope
    if envelope_status == "completed":
        agreement = db.query(Agreement).filter(
            Agreement.id == envelope.agreement_id
        ).first()
        
        if agreement:
            agreement.status = "completed"
            
            # Mark all parties as signed
            for party in agreement.parties:
                if not party.signed:
                    party.signed = True
                    from datetime import datetime
                    party.signed_at = datetime.utcnow()
            
            # Send completion notification
            try:
                party_emails = [p.email for p in agreement.parties]
                download_link = f"{settings.frontend_url}/agreements/{agreement.id}/download"
                notification_service.send_completion_email(
                    to_emails=party_emails,
                    agreement_title=agreement.title,
                    download_link=download_link
                )
            except Exception:
                pass  # Notification not configured
    
    # Handle voided envelope
    elif envelope_status == "voided":
        agreement = db.query(Agreement).filter(
            Agreement.id == envelope.agreement_id
        ).first()
        
        if agreement:
            agreement.status = "void"
    
    db.commit()
    
    return {"received": True}


@router.post("/kyc/{provider}")
async def kyc_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle KYC provider webhook events.
    
    For Persona: expects X-Persona-Signature header
    """
    from app.models.models import IdVerification
    from app.services.kyc import kyc_service
    
    if provider not in ["idme", "onfido", "persona"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown KYC provider"
        )
    
    # Get raw body for signature verification
    body = await request.body()
    
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Get appropriate signature header based on provider
    if provider == "persona":
        signature = request.headers.get("X-Persona-Signature")
        # Verify Persona webhook signature
        if signature and not kyc_service.verify_persona_webhook(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    else:
        signature = request.headers.get("X-Webhook-Signature")
    
    try:
        result = kyc_service.process_webhook(provider, payload, signature)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Update verification record
    # For Persona: use reference_id (our user_id) to find the verification
    # since inquiry_id may not be stored when SDK creates inquiry on load
    if provider == "persona":
        user_id = result.get("reference_id")  # This is our user.id
        inquiry_id = result.get("verification_id")  # This is the Persona inquiry_id
        
        # Find the most recent pending Persona verification for this user
        verification = db.query(IdVerification).filter(
            IdVerification.user_id == user_id,
            IdVerification.provider == "persona",
            IdVerification.status == "pending"
        ).first()
        
        # If not found by user_id, try by inquiry_id (in case it was already set)
        if not verification and inquiry_id:
            verification = db.query(IdVerification).filter(
                IdVerification.reference_id == inquiry_id,
                IdVerification.provider == "persona"
            ).first()
    else:
        # Other providers: look up by reference_id
        verification = db.query(IdVerification).filter(
            IdVerification.reference_id == result.get("verification_id"),
            IdVerification.provider == provider
        ).first()
    
    if verification:
        # Update the inquiry_id reference if it was missing
        if provider == "persona" and result.get("verification_id"):
            verification.reference_id = result.get("verification_id")
        
        verification.status = result.get("status", "pending")
        if result.get("completed_at"):
            from datetime import datetime
            try:
                verification.completed_at = datetime.fromisoformat(result["completed_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                verification.completed_at = datetime.utcnow()
        
        # Update user verification status if approved
        if verification.status == "approved":
            from app.models.models import AppUser
            user = db.query(AppUser).filter(AppUser.id == verification.user_id).first()
            if user:
                user.is_verified = True
        
        db.commit()
    
    return {"received": True}
