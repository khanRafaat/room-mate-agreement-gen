"""
Roommate Agreement Generator - Payment Schemas
Pydantic schemas for payment-related request/response validation
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class PaymentCreate(BaseModel):
    """Schema for initiating a payment."""
    method: str  # 'solana', 'card'


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: UUID
    agreement_id: UUID
    method: str
    amount_cents: int
    currency: str
    status: str
    provider_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CheckoutResponse(BaseModel):
    """Schema for checkout session response."""
    payment_id: UUID
    method: str
    checkout_url: str


class CheckoutLinks(BaseModel):
    """Schema for multiple checkout options."""
    card: Optional[CheckoutResponse] = None
    crypto: Optional[CheckoutResponse] = None


class PaymentWebhookEvent(BaseModel):
    """Schema for payment webhook event data."""
    event_type: str
    payment_id: Optional[str] = None
    agreement_id: Optional[str] = None
    status: str
    provider_ref: Optional[str] = None
    raw_payload: Optional[dict] = None
