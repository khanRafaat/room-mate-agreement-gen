"""
Roommate Agreement Generator - File Schemas
Pydantic schemas for file-related request/response validation
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class FileAssetBase(BaseModel):
    """Base file asset schema."""
    kind: str  # 'lease_first_page', 'govt_id', 'agreement_pdf', 'signed_pdf'
    container: str


class FileAssetCreate(FileAssetBase):
    """Schema for creating a file asset record."""
    blob_name: str
    size_bytes: Optional[int] = None


class FileAssetResponse(FileAssetBase):
    """Schema for file asset response."""
    id: UUID
    owner_id: UUID
    blob_name: str
    size_bytes: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SASRequest(BaseModel):
    """Schema for requesting a SAS token."""
    kind: str  # 'lease_first_page', 'govt_id', 'agreement_pdf', 'signed_pdf'
    filename: str


class SASResponse(BaseModel):
    """Schema for SAS token response."""
    url: str
    blob_name: str
    expires_at: datetime


class UploadComplete(BaseModel):
    """Schema for confirming upload completion."""
    blob_name: str
    kind: str
    size_bytes: int
    container: str = "agreements"
