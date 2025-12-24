"""
Roommate Agreement Generator - User Schemas
Pydantic schemas for user-related request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    b2c_sub: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class IdVerificationCreate(BaseModel):
    """Schema for starting ID verification."""
    provider: str  # 'idme', 'onfido', 'persona'


class IdVerificationResponse(BaseModel):
    """Schema for ID verification response."""
    id: UUID
    provider: str
    status: str
    reference_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
