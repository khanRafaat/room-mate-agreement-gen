"""
Roommate Agreement Generator - DocuSign Service
DocuSign eSignature integration for envelope creation and signing
"""
import base64
import os
from typing import List, Optional

from app.config import get_settings

settings = get_settings()

# Conditional import for DocuSign SDK
try:
    from docusign_esign import (
        ApiClient,
        EnvelopesApi,
        EnvelopeDefinition,
        Document,
        Signer,
        SignHere,
        Tabs,
        Recipients,
        RecipientViewRequest
    )
    DOCUSIGN_AVAILABLE = True
except ImportError:
    DOCUSIGN_AVAILABLE = False


class DocuSignService:
    """DocuSign eSignature service for envelope management."""
    
    def __init__(self):
        """Initialize the DocuSign service."""
        self._api_client: Optional[object] = None
    
    @property
    def api_client(self):
        """Get or create the DocuSign API client."""
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        if self._api_client is None:
            if not settings.docusign_access_token:
                raise ValueError("DocuSign access token not configured")
            
            self._api_client = ApiClient()
            self._api_client.host = settings.docusign_base_url
            self._api_client.set_default_header(
                "Authorization",
                f"Bearer {settings.docusign_access_token}"
            )
        
        return self._api_client
    
    def create_envelope(
        self,
        pdf_bytes: bytes,
        recipients: List[dict],
        email_subject: str = "Please sign your roommate agreement",
        document_name: str = "Roommate Agreement"
    ) -> str:
        """
        Create and send a DocuSign envelope.
        
        Args:
            pdf_bytes: PDF document content
            recipients: List of recipient dicts with email, name, and optionally routing_order
            email_subject: Email subject for the envelope
            document_name: Name of the document
            
        Returns:
            Envelope ID
        """
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        # Encode document
        doc_b64 = base64.b64encode(pdf_bytes).decode()
        
        document = Document(
            document_base64=doc_b64,
            name=document_name,
            file_extension="pdf",
            document_id="1"
        )
        
        # Create signers with tabs
        signers = []
        for i, r in enumerate(recipients, start=1):
            signer = Signer(
                email=r["email"],
                name=r["name"],
                recipient_id=str(i),
                routing_order=str(r.get("routing_order", i))
            )
            
            # Add signature tab
            sign_here = SignHere(
                document_id="1",
                page_number="1",
                x_position=str(100 + (i - 1) * 150),
                y_position="700"
            )
            signer.tabs = Tabs(sign_here_tabs=[sign_here])
            
            signers.append(signer)
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=email_subject,
            documents=[document],
            recipients=Recipients(signers=signers),
            status="sent"
        )
        
        # Send envelope
        envelopes_api = EnvelopesApi(self.api_client)
        result = envelopes_api.create_envelope(
            account_id=settings.docusign_account_id,
            envelope_definition=envelope_definition
        )
        
        return result.envelope_id
    
    def get_signing_url(
        self,
        envelope_id: str,
        signer_email: str,
        signer_name: str,
        return_url: str
    ) -> str:
        """
        Get an embedded signing URL for a recipient.
        
        Args:
            envelope_id: DocuSign envelope ID
            signer_email: Signer's email
            signer_name: Signer's name
            return_url: URL to redirect after signing
            
        Returns:
            Embedded signing URL
        """
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        recipient_view_request = RecipientViewRequest(
            authentication_method="none",
            client_user_id=signer_email,
            recipient_id="1",
            return_url=return_url,
            user_name=signer_name,
            email=signer_email
        )
        
        envelopes_api = EnvelopesApi(self.api_client)
        result = envelopes_api.create_recipient_view(
            account_id=settings.docusign_account_id,
            envelope_id=envelope_id,
            recipient_view_request=recipient_view_request
        )
        
        return result.url
    
    def get_envelope_status(self, envelope_id: str) -> dict:
        """
        Get the status of an envelope.
        
        Args:
            envelope_id: DocuSign envelope ID
            
        Returns:
            Envelope status dict
        """
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        envelopes_api = EnvelopesApi(self.api_client)
        result = envelopes_api.get_envelope(
            account_id=settings.docusign_account_id,
            envelope_id=envelope_id
        )
        
        return {
            "envelope_id": result.envelope_id,
            "status": result.status,
            "sent_date_time": result.sent_date_time,
            "completed_date_time": result.completed_date_time
        }
    
    def download_signed_document(self, envelope_id: str, document_id: str = "1") -> bytes:
        """
        Download a signed document from an envelope.
        
        Args:
            envelope_id: DocuSign envelope ID
            document_id: Document ID within the envelope
            
        Returns:
            Document bytes
        """
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        envelopes_api = EnvelopesApi(self.api_client)
        return envelopes_api.get_document(
            account_id=settings.docusign_account_id,
            envelope_id=envelope_id,
            document_id=document_id
        )
    
    def void_envelope(self, envelope_id: str, void_reason: str = "Voided by user") -> bool:
        """
        Void an envelope.
        
        Args:
            envelope_id: DocuSign envelope ID
            void_reason: Reason for voiding
            
        Returns:
            True if voided successfully
        """
        if not DOCUSIGN_AVAILABLE:
            raise ImportError("docusign-esign package is not installed")
        
        envelope_update = {"status": "voided", "voidedReason": void_reason}
        
        envelopes_api = EnvelopesApi(self.api_client)
        envelopes_api.update(
            account_id=settings.docusign_account_id,
            envelope_id=envelope_id,
            envelope=envelope_update
        )
        
        return True


# Singleton instance
docusign_service = DocuSignService()
