"""
Roommate Agreement Generator - Payments Service
Stripe and Coinbase Commerce integration
"""
import stripe
import hmac
import hashlib
import requests
from typing import Optional

from app.config import get_settings

settings = get_settings()

# Configure Stripe
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class PaymentsService:
    """Payment service for Stripe and Coinbase Commerce."""
    
    COINBASE_API_URL = "https://api.commerce.coinbase.com/charges"
    
    def start_card_checkout(
        self,
        agreement_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> dict:
        """
        Create a Stripe Checkout session for card payment.
        
        Args:
            agreement_id: Agreement ID for metadata
            success_url: Redirect URL after successful payment
            cancel_url: Redirect URL if payment is cancelled
            
        Returns:
            Dict with session_id and url
        """
        if not settings.stripe_secret_key:
            raise ValueError("Stripe secret key not configured")
        
        base_url = settings.frontend_url
        
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Roommate Agreement",
                        "description": "Create and e-sign your roommate agreement"
                    },
                    "unit_amount": settings.stripe_price_cents,
                },
                "quantity": 1
            }],
            success_url=success_url or f"{base_url}/agreements/{agreement_id}?paid=1",
            cancel_url=cancel_url or f"{base_url}/agreements/{agreement_id}?canceled=1",
            metadata={"agreement_id": agreement_id}
        )
        
        return {
            "session_id": session.id,
            "url": session.url,
            "provider": "stripe"
        }
    
    def start_crypto_checkout(
        self,
        agreement_id: str,
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> dict:
        """
        Create a Coinbase Commerce charge for crypto payment.
        
        Args:
            agreement_id: Agreement ID for metadata
            redirect_url: Redirect URL after successful payment
            cancel_url: Redirect URL if payment is cancelled
            
        Returns:
            Dict with charge_id and hosted_url
        """
        if not settings.coinbase_commerce_key:
            raise ValueError("Coinbase Commerce key not configured")
        
        base_url = settings.frontend_url
        
        headers = {
            "X-CC-Api-Key": settings.coinbase_commerce_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": "Roommate Agreement",
            "description": "Create and e-sign your roommate agreement",
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": settings.coinbase_price_usd,
                "currency": "USD"
            },
            "metadata": {"agreement_id": agreement_id},
            "redirect_url": redirect_url or f"{base_url}/agreements/{agreement_id}?paid=1",
            "cancel_url": cancel_url or f"{base_url}/agreements/{agreement_id}?canceled=1"
        }
        
        response = requests.post(
            self.COINBASE_API_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()["data"]
        
        return {
            "charge_id": data["id"],
            "url": data["hosted_url"],
            "provider": "coinbase"
        }
    
    def verify_stripe_webhook(self, payload: bytes, signature: str) -> dict:
        """
        Verify and parse a Stripe webhook event.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Parsed event object
        """
        if not settings.stripe_webhook_secret:
            raise ValueError("Stripe webhook secret not configured")
        
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret
        )
        
        return event
    
    def verify_coinbase_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Verify a Coinbase Commerce webhook signature.
        
        Args:
            payload: Raw request body
            signature: X-CC-Webhook-Signature header
            
        Returns:
            True if signature is valid
        """
        if not settings.coinbase_commerce_webhook_secret:
            raise ValueError("Coinbase Commerce webhook secret not configured")
        
        computed_signature = hmac.new(
            settings.coinbase_commerce_webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    def get_stripe_session(self, session_id: str) -> dict:
        """
        Retrieve a Stripe Checkout session.
        
        Args:
            session_id: Stripe session ID
            
        Returns:
            Session object
        """
        return stripe.checkout.Session.retrieve(session_id)


# Singleton instance
payments_service = PaymentsService()
