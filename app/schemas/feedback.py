"""
Roommate Agreement Generator - Feedback Schemas
Pydantic schemas for roommate feedback and ratings
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class CategoryRatings(BaseModel):
    """Category-specific ratings."""
    cleanliness: Optional[int] = Field(None, ge=1, le=5)
    communication: Optional[int] = Field(None, ge=1, le=5)
    respect: Optional[int] = Field(None, ge=1, le=5)
    reliability: Optional[int] = Field(None, ge=1, le=5)
    noise_level: Optional[int] = Field(None, ge=1, le=5)


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    to_user_id: str
    rating: int = Field(..., ge=1, le=5, description="Overall rating 1-5 stars")
    comment: Optional[str] = Field(None, max_length=1000)
    categories: Optional[CategoryRatings] = None
    is_anonymous: bool = False


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: str
    agreement_id: str
    from_user_id: Optional[str] = None  # Hidden if anonymous
    from_user_name: Optional[str] = None
    to_user_id: str
    to_user_name: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    categories: Optional[Dict] = None
    is_anonymous: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackSummary(BaseModel):
    """Schema for user's feedback summary."""
    user_id: str
    user_name: Optional[str] = None
    total_ratings: int
    average_rating: float
    category_averages: Optional[Dict[str, float]] = None
    recent_feedback: List[FeedbackResponse] = []


class InviteTokenResponse(BaseModel):
    """Schema for invite token response."""
    token: str
    email: str
    expires_at: datetime
    invite_url: str


class AcceptInviteRequest(BaseModel):
    """Schema for accepting an invite."""
    token: str
