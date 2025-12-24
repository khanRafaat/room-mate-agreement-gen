"""
Roommate Agreement Generator - Agreement Schemas
Pydantic schemas for agreement-related request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from uuid import UUID


class QuietHours(BaseModel):
    """Quiet hours configuration."""
    start: str  # e.g., "22:00"
    end: str    # e.g., "07:00"


class GuestRules(BaseModel):
    """Guest rules configuration."""
    max_consecutive_nights: int = 3
    notice_hours: int = 24


class PetRules(BaseModel):
    """Pet rules configuration."""
    allowed: bool = False
    notes: Optional[str] = None


class AgreementTermsBase(BaseModel):
    """Base agreement terms schema."""
    quiet_hours: Optional[QuietHours] = None
    guest_rules: Optional[GuestRules] = None
    pet_rules: Optional[PetRules] = None
    deposit_cents: Optional[int] = None
    deposit_forfeit_reasons: Optional[List[str]] = None
    additional_rules: Optional[str] = None
    no_offensive_clause_ack: bool = False


class AgreementTermsCreate(AgreementTermsBase):
    """Schema for creating agreement terms."""
    pass


class AgreementTermsResponse(AgreementTermsBase):
    """Schema for agreement terms response."""
    
    class Config:
        from_attributes = True


class AgreementPartyBase(BaseModel):
    """Base agreement party schema."""
    email: EmailStr
    phone: Optional[str] = None
    role: str = "roommate"  # 'initiator', 'roommate'
    rent_share_cents: Optional[int] = None
    utilities: Optional[Dict[str, Any]] = None
    chores: Optional[Dict[str, Any]] = None


class AgreementPartyCreate(AgreementPartyBase):
    """Schema for creating an agreement party."""
    pass


class AgreementPartyResponse(AgreementPartyBase):
    """Schema for agreement party response."""
    id: UUID
    user_id: Optional[UUID] = None
    signed: bool
    signed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AgreementBase(BaseModel):
    """Base agreement schema."""
    title: str = "Roommate Agreement"
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_total_cents: int


class AgreementCreate(AgreementBase):
    """Schema for creating an agreement."""
    terms: Optional[AgreementTermsCreate] = None
    parties: Optional[List[AgreementPartyCreate]] = None


class AgreementResponse(AgreementBase):
    """Schema for agreement response."""
    id: UUID
    initiator_id: UUID
    status: str
    created_at: datetime
    terms: Optional[AgreementTermsResponse] = None
    parties: List[AgreementPartyResponse] = []
    
    class Config:
        from_attributes = True


class AgreementListResponse(BaseModel):
    """Schema for listing agreements."""
    id: UUID
    title: str
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgreementUpdate(BaseModel):
    """Schema for updating an agreement."""
    title: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_total_cents: Optional[int] = None


class InviteRequest(BaseModel):
    """Schema for inviting roommates."""
    roommates: List[AgreementPartyCreate]
