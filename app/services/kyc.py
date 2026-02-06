"""
Roommate Agreement Generator - KYC Service
Identity verification integration with Persona embedded flow
"""
import hmac
import hashlib
import requests
from typing import Optional
from datetime import datetime

from app.config import get_settings

settings = get_settings()


class KYCService:
    """KYC service for identity verification using Persona."""
    
    PERSONA_API_BASE = "https://withpersona.com/api/v1"
    
    # Provider URLs (placeholder for future providers)
    PROVIDERS = {
        "idme": "https://api.id.me/",
        "onfido": "https://api.onfido.com/v3/",
        "persona": "https://withpersona.com/api/v1/"
    }
    
    def __init__(self):
        """Initialize the KYC service."""
        self.persona_api_key = settings.persona_api_key
        self.persona_template_id = settings.persona_template_id
        self.persona_environment_id = settings.persona_environment_id
        self.persona_webhook_secret = settings.persona_webhook_secret
    
    def _get_persona_headers(self) -> dict:
        """Get headers for Persona API calls."""
        if not self.persona_api_key:
            raise ValueError("Persona API key not configured")
        return {
            "Authorization": f"Bearer {self.persona_api_key}",
            "Persona-Version": "2023-01-05",
            "Content-Type": "application/json"
        }
    
    def create_persona_inquiry(
        self,
        user_id: str,
        user_email: str
    ) -> dict:
        """
        Create a Persona inquiry for embedded flow.
        
        Args:
            user_id: Internal user ID for reference
            user_email: User's email address
            
        Returns:
            Dict with inquiry_id, template_id, environment_id for SDK
        """
        if not self.persona_template_id or not self.persona_environment_id:
            raise ValueError("Persona template_id or environment_id not configured")
        
        # For embedded flow, we can either:
        # 1. Just return template/env IDs (SDK creates inquiry on load)
        # 2. Pre-create inquiry via API (recommended for production)
        
        # Option 1: Simple embedded flow (SDK creates inquiry)
        # This is suitable for sandbox/testing
        return {
            "inquiry_id": None,  # SDK will create
            "template_id": self.persona_template_id,
            "environment_id": self.persona_environment_id,
            "reference_id": user_id  # Link back to our user
        }
    
    def create_persona_inquiry_via_api(
        self,
        user_id: str,
        user_email: str
    ) -> dict:
        """
        Pre-create a Persona inquiry via API (production recommended).
        
        Args:
            user_id: Internal user ID for reference
            user_email: User's email address
            
        Returns:
            Dict with inquiry_id, template_id, environment_id for SDK
        """
        if not self.persona_api_key:
            raise ValueError("Persona API key not configured")
        
        url = f"{self.PERSONA_API_BASE}/inquiries"
        payload = {
            "data": {
                "attributes": {
                    "inquiry-template-id": self.persona_template_id,
                    "reference-id": user_id,
                    "fields": {
                        "email-address": user_email
                    }
                }
            }
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=self._get_persona_headers()
        )
        
        if response.status_code != 201:
            raise ValueError(f"Failed to create Persona inquiry: {response.text}")
        
        data = response.json()
        inquiry_id = data.get("data", {}).get("id")
        
        return {
            "inquiry_id": inquiry_id,
            "template_id": self.persona_template_id,
            "environment_id": self.persona_environment_id,
            "reference_id": user_id
        }
    
    def get_persona_inquiry(self, inquiry_id: str) -> dict:
        """
        Get inquiry details from Persona API.
        
        Args:
            inquiry_id: Persona inquiry ID
            
        Returns:
            Inquiry details including status
        """
        url = f"{self.PERSONA_API_BASE}/inquiries/{inquiry_id}"
        
        response = requests.get(
            url,
            headers=self._get_persona_headers()
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get Persona inquiry: {response.text}")
        
        data = response.json()
        attributes = data.get("data", {}).get("attributes", {})
        
        return {
            "inquiry_id": inquiry_id,
            "status": attributes.get("status"),
            "reference_id": attributes.get("reference-id"),
            "completed_at": attributes.get("completed-at"),
            "created_at": attributes.get("created-at")
        }
    
    def verify_persona_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Verify Persona webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature: X-Persona-Signature header value
            
        Returns:
            True if signature is valid
        """
        if not self.persona_webhook_secret:
            # If no secret configured, accept webhook (sandbox mode)
            return True
        
        # Persona uses HMAC-SHA256 for webhook signatures
        # Format: t=timestamp,v1=signature
        try:
            parts = dict(p.split("=", 1) for p in signature.split(","))
            timestamp = parts.get("t", "")
            provided_sig = parts.get("v1", "")
            
            # Create expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected_sig = hmac.new(
                self.persona_webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_sig, provided_sig)
        except Exception:
            return False
    
    def start_verification(
        self,
        provider: str,
        user_email: str,
        callback_url: str
    ) -> dict:
        """
        Start an ID verification session.
        
        Args:
            provider: Verification provider ('persona')
            user_email: User's email for the verification
            callback_url: URL to redirect after verification
            
        Returns:
            Dict with verification data for embedded flow
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        
        if provider == "persona":
            # For Persona, return embedded flow configuration
            # inquiry_id will be None (created by SDK) or pre-created
            return {
                "verification_id": None,  # Created by SDK
                "template_id": self.persona_template_id,
                "environment_id": self.persona_environment_id,
                "provider": "persona",
                # No redirect_url for embedded flow
                "redirect_url": None
            }
        
        # Fallback for other providers (not implemented)
        raise ValueError(f"Provider {provider} not implemented")
    
    def check_verification_status(
        self,
        provider: str,
        verification_id: str
    ) -> dict:
        """
        Check the status of a verification.
        
        Args:
            provider: Verification provider
            verification_id: Provider-specific verification ID
            
        Returns:
            Dict with status and details
        """
        if provider == "persona":
            return self.get_persona_inquiry(verification_id)
        
        raise ValueError(f"Provider {provider} not implemented")
    
    def process_webhook(
        self,
        provider: str,
        payload: dict,
        signature: Optional[str] = None
    ) -> dict:
        """
        Process a verification webhook callback.
        
        Args:
            provider: Verification provider
            payload: Webhook payload
            signature: Webhook signature for verification
            
        Returns:
            Processed verification result
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        
        if provider == "persona":
            return self._process_persona_webhook(payload)
        
        # Fallback for other providers
        return {
            "verification_id": payload.get("verification_id"),
            "provider": provider,
            "status": payload.get("status", "pending"),
            "reference_id": payload.get("reference_id"),
            "completed_at": payload.get("completed_at")
        }
    
    def _process_persona_webhook(self, payload: dict) -> dict:
        """
        Process Persona-specific webhook payload.
        
        Persona webhook events:
        - inquiry.created
        - inquiry.started
        - inquiry.completed
        - inquiry.approved
        - inquiry.declined
        - inquiry.expired
        """
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        
        inquiry_id = data.get("id")
        status = attributes.get("status", "pending")
        reference_id = attributes.get("reference-id")
        completed_at = attributes.get("completed-at")
        
        # Map Persona status to our status
        status_mapping = {
            "created": "pending",
            "pending": "pending",
            "started": "pending",
            "completed": "pending",  # Completed but not yet reviewed
            "approved": "approved",
            "declined": "rejected",
            "expired": "rejected",
            "failed": "rejected",
            "needs_review": "pending"
        }
        
        mapped_status = status_mapping.get(status, "pending")
        
        return {
            "verification_id": inquiry_id,
            "provider": "persona",
            "status": mapped_status,
            "reference_id": reference_id,
            "completed_at": completed_at
        }


# Singleton instance
kyc_service = KYCService()
