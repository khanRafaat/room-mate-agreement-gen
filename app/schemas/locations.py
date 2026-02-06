"""
Schemas for Location (Country, State, City) and Base Agreement endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ==================== LOCATION SCHEMAS ====================

class CountryResponse(BaseModel):
    """Country response for dropdown."""
    id: str
    code: str
    name: str

    class Config:
        from_attributes = True


class StateResponse(BaseModel):
    """State response for dropdown."""
    id: str
    country_id: str
    code: Optional[str] = None
    name: str

    class Config:
        from_attributes = True


class CityResponse(BaseModel):
    """City response for dropdown."""
    id: str
    state_id: str
    name: str

    class Config:
        from_attributes = True


# ==================== BASE AGREEMENT SCHEMAS ====================

class BaseAgreementSummary(BaseModel):
    """Summary for embedding in agreement responses."""
    id: str
    title: str
    version: str
    city_name: Optional[str] = None
    state_name: Optional[str] = None
    country_name: Optional[str] = None
    has_pdf: bool = False  # Indicates if PDF is available

    class Config:
        from_attributes = True


class BaseAgreementResponse(BaseModel):
    """Full base agreement response."""
    id: str
    city_id: str
    city_name: str
    state_name: str
    country_name: str
    title: str
    version: str
    content: Optional[str] = None
    applicable_for: str = "both"  # 'landlord', 'tenant', 'both'
    is_active: bool = True
    effective_date: Optional[date] = None
    created_at: Optional[datetime] = None
    
    # PDF file info
    pdf_filename: Optional[str] = None
    pdf_size_bytes: Optional[int] = None
    pdf_url: Optional[str] = None  # Pre-signed download URL (when available)
    has_pdf: bool = False

    class Config:
        from_attributes = True


class BaseAgreementCreate(BaseModel):
    """Create a new base agreement."""
    city_id: Optional[str] = None  # Optional - can use city_name instead
    city_name: Optional[str] = None  # Free-form city name text
    title: str
    version: str = "1.0.0"
    content: Optional[str] = None
    applicable_for: str = Field(default="both", pattern="^(landlord|tenant|both)$")
    effective_date: Optional[date] = None


class BaseAgreementUpdate(BaseModel):
    """Update a base agreement."""
    title: Optional[str] = None
    version: Optional[str] = None
    content: Optional[str] = None
    applicable_for: Optional[str] = None
    is_active: Optional[bool] = None
    effective_date: Optional[date] = None


class BaseAgreementPdfUpload(BaseModel):
    """Request to attach uploaded PDF to base agreement."""
    blob_name: str  # From upload-sas response
    filename: str   # Original filename
    size_bytes: int
    container: str = "base-agreements"


class Base64FileUpload(BaseModel):
    """Request for base64 file upload."""
    filename: str  # Original filename
    content_base64: str  # Base64 encoded file content
    content_type: Optional[str] = "application/pdf"


class FileUploadResponse(BaseModel):
    """Response for file upload with URLs."""
    success: bool
    filename: str
    size_bytes: int
    download_url: str
    preview_url: str
    blob_name: str
