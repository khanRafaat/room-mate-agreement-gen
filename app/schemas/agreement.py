"""
Roommate Agreement Generator - Agreement Schemas
Pydantic schemas for agreement-related request/response validation
"""
from pydantic import BaseModel, EmailStr, field_validator
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
    requires_id_verification: bool = False  # Owner wants tenant to verify ID


class AgreementPartyCreate(AgreementPartyBase):
    """Schema for creating an agreement party."""
    pass


class AgreementPartyResponse(AgreementPartyBase):
    """Schema for agreement party response."""
    id: UUID
    user_id: Optional[UUID] = None
    id_verified: bool = False  # Tenant has verified their ID
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
    
    # Convert empty strings to None for date fields
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v
    
    # Convert empty strings to None for optional string fields
    @field_validator('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class AgreementCreate(AgreementBase):
    """Schema for creating an agreement."""
    base_agreement_id: Optional[str] = None  # Link to city-specific base agreement
    owner_name: Optional[str] = None  # Landlord/Owner name
    terms: Optional[AgreementTermsCreate] = None
    parties: Optional[List[AgreementPartyCreate]] = None


class BaseAgreementSummaryEmbed(BaseModel):
    """Embedded base agreement summary in agreement response."""
    id: str
    title: str
    version: str
    city_name: Optional[str] = None
    state_name: Optional[str] = None
    country_name: Optional[str] = None

    class Config:
        from_attributes = True


class AgreementResponse(AgreementBase):
    """Schema for agreement response."""
    id: UUID
    initiator_id: UUID
    base_agreement_id: Optional[str] = None
    owner_name: Optional[str] = None
    tenant_name: Optional[str] = None
    status: str
    created_at: datetime
    terms: Optional[AgreementTermsResponse] = None
    parties: List[AgreementPartyResponse] = []
    base_agreement: Optional[BaseAgreementSummaryEmbed] = None
    
    class Config:
        from_attributes = True


class AgreementListResponse(BaseModel):
    """Schema for listing agreements."""
    id: UUID
    initiator_id: UUID
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
    base_agreement_id: Optional[str] = None
    owner_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_total_cents: Optional[int] = None
    
    # Convert empty strings to None for date fields
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v
    
    # Convert empty strings to None for optional string fields
    @field_validator('title', 'base_agreement_id', 'owner_name', 'address_line1', 'address_line2', 
                     'city', 'state', 'postal_code', 'country', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class InviteRequest(BaseModel):
    """Schema for inviting roommates."""
    roommates: List[AgreementPartyCreate]
