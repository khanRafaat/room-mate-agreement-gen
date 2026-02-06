"""
Roommate Agreement Generator - Base Agreements Router
API endpoints for managing base agreement templates.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import BaseAgreement, City, State, Country
from app.schemas.locations import (
    BaseAgreementResponse, 
    BaseAgreementCreate, 
    BaseAgreementUpdate,
    BaseAgreementSummary,
    BaseAgreementPdfUpload,
    Base64FileUpload,
    FileUploadResponse
)
from app.deps.auth import get_current_user, CurrentUser
from app.services.storage import storage_service

router = APIRouter(prefix="/base-agreements", tags=["base-agreements"])

# Container for base agreement PDFs
BASE_AGREEMENT_CONTAINER = "base-agreements"


def _build_base_agreement_response(base_agreement: BaseAgreement, include_pdf_url: bool = True) -> dict:
    """Build response with city, state, country names and PDF URL."""
    city = base_agreement.city
    state = city.state if city else None
    country = state.country if state else None
    
    # Use city_name column for custom cities, or city.name from relationship
    city_name = base_agreement.city_name or (city.name if city else None)
    
    has_pdf = bool(base_agreement.pdf_blob_name)
    pdf_url = None
    
    # Generate pre-signed download URL if PDF exists
    if include_pdf_url and has_pdf:
        try:
            result = storage_service.generate_download_sas(
                container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
                blob_name=base_agreement.pdf_blob_name,
                expiry_minutes=60
            )
            pdf_url = result["url"]
        except Exception:
            pass  # Storage may not be configured
    
    return {
        "id": base_agreement.id,
        "city_id": base_agreement.city_id or "",
        "city_name": city_name or "",
        "state_name": state.name if state else "",
        "country_name": country.name if country else None,
        "title": base_agreement.title,
        "version": base_agreement.version,
        "content": base_agreement.content,
        "applicable_for": base_agreement.applicable_for,
        "is_active": base_agreement.is_active,
        "effective_date": base_agreement.effective_date,
        "created_at": base_agreement.created_at,
        "pdf_filename": base_agreement.pdf_filename,
        "pdf_size_bytes": base_agreement.pdf_size_bytes,
        "pdf_url": pdf_url,
        "has_pdf": has_pdf,
    }


@router.get("/city/{city_id}", response_model=BaseAgreementResponse)
async def get_base_agreement_by_city(
    city_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the active base agreement for a specific city.
    
    This is the main endpoint for frontend to load the base agreement
    after user selects Country → State → City.
    
    Returns the agreement with a pre-signed PDF download URL if available.
    """
    # Verify city exists
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found"
        )
    
    # Get active base agreement for this city
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.city_id == city_id,
        BaseAgreement.is_active == True
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No base agreement found for {city.name}. Please contact support."
        )
    
    return _build_base_agreement_response(base_agreement)


@router.get("/{agreement_id}", response_model=BaseAgreementResponse)
async def get_base_agreement(
    agreement_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific base agreement by ID.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    return _build_base_agreement_response(base_agreement)


@router.get("", response_model=List[BaseAgreementSummary])
async def list_base_agreements(
    city_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    List base agreements (admin endpoint).
    
    Query params:
    - city_id: Filter by city
    - is_active: Filter by active status
    """
    query = db.query(BaseAgreement)
    
    if city_id:
        query = query.filter(BaseAgreement.city_id == city_id)
    
    if is_active is not None:
        query = query.filter(BaseAgreement.is_active == is_active)
    
    base_agreements = query.order_by(BaseAgreement.created_at.desc()).limit(100).all()
    
    result = []
    for ba in base_agreements:
        city = ba.city
        state = city.state if city else None
        country = state.country if state else None
        
        result.append({
            "id": ba.id,
            "title": ba.title,
            "version": ba.version,
            "city_name": city.name if city else None,
            "state_name": state.name if state else None,
            "country_name": country.name if country else None,
            "has_pdf": bool(ba.pdf_blob_name),
        })
    
    return result


@router.post("", response_model=BaseAgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_base_agreement(
    body: BaseAgreementCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new base agreement (admin endpoint).
    
    Accepts either:
    - city_id: An existing city ID from the database
    - city_name: A free-form city name (no database lookup required)
    
    Note: Only one base agreement should be active per city.
    Creating a new one will NOT automatically deactivate others.
    """
    city = None
    city_id_to_use = None
    city_name_to_use = body.city_name or ""
    
    # If city_id is provided, try to look up the city
    if body.city_id:
        # If city_id starts with "custom-", it's a user-typed city name
        if body.city_id.startswith("custom-"):
            # No database lookup - use the city_name directly
            city_id_to_use = None
            if not city_name_to_use:
                # Extract city name from custom-xxx format
                city_name_to_use = body.city_id.replace("custom-", "").replace("-", " ").title()
        else:
            # Try to find the city in database
            city = db.query(City).filter(City.id == body.city_id).first()
            if not city:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="City not found"
                )
            city_id_to_use = city.id
            city_name_to_use = city.name
    
    # Create base agreement
    base_agreement = BaseAgreement(
        city_id=city_id_to_use,  # Will be None for custom cities
        city_name=city_name_to_use,  # Store the city name text
        title=body.title,
        version=body.version,
        content=body.content,
        applicable_for=body.applicable_for,
        effective_date=body.effective_date,
        is_active=True,
    )
    
    db.add(base_agreement)
    db.commit()
    db.refresh(base_agreement)
    
    # Build response
    state_name = city.state.name if city and city.state else ""
    country_name = city.state.country.name if city and city.state and city.state.country else ""
    
    return {
        "id": base_agreement.id,
        "city_id": base_agreement.city_id or "",
        "city_name": base_agreement.city_name or "",
        "state_name": state_name,
        "country_name": country_name,
        "title": base_agreement.title,
        "version": base_agreement.version,
        "content": base_agreement.content,
        "applicable_for": base_agreement.applicable_for,
        "is_active": base_agreement.is_active,
        "effective_date": base_agreement.effective_date,
        "created_at": base_agreement.created_at,
        "pdf_filename": base_agreement.pdf_filename,
        "pdf_size_bytes": base_agreement.pdf_size_bytes,
        "pdf_url": None,
        "has_pdf": bool(base_agreement.pdf_blob_name),
    }


@router.patch("/{agreement_id}", response_model=BaseAgreementResponse)
async def update_base_agreement(
    agreement_id: str,
    body: BaseAgreementUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update a base agreement (admin endpoint).
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    # Update fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(base_agreement, field, value)
    
    db.commit()
    db.refresh(base_agreement)
    
    return _build_base_agreement_response(base_agreement)


@router.delete("/{agreement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_base_agreement(
    agreement_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete a base agreement (admin endpoint).
    
    Warning: This will fail if agreements are linked to this base agreement.
    Consider deactivating instead.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    # Check if any agreements are linked
    if base_agreement.agreements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete: This base agreement is linked to existing agreements. Deactivate instead."
        )
    
    # Delete associated PDF from storage
    if base_agreement.pdf_blob_name:
        try:
            storage_service.delete_blob(
                container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
                blob_name=base_agreement.pdf_blob_name
            )
        except Exception:
            pass  # Blob may already be deleted
    
    db.delete(base_agreement)
    db.commit()
    
    return None


@router.post("/{agreement_id}/deactivate", response_model=BaseAgreementResponse)
async def deactivate_base_agreement(
    agreement_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Deactivate a base agreement (admin endpoint).
    
    Deactivated agreements won't appear in city lookups.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    base_agreement.is_active = False
    db.commit()
    db.refresh(base_agreement)
    
    return _build_base_agreement_response(base_agreement)


@router.post("/{agreement_id}/activate", response_model=BaseAgreementResponse)
async def activate_base_agreement(
    agreement_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Activate a base agreement (admin endpoint).
    
    Note: Multiple active agreements per city are allowed but not recommended.
    The city lookup will return the first one found.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    base_agreement.is_active = True
    db.commit()
    db.refresh(base_agreement)
    
    return _build_base_agreement_response(base_agreement)


# ==================== PDF UPLOAD ENDPOINTS ====================


@router.post("/{agreement_id}/pdf/upload-sas")
async def get_pdf_upload_sas(
    agreement_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a SAS token for uploading a PDF to the base agreement.
    
    The frontend should:
    1. Call this endpoint to get upload URL
    2. Upload PDF directly to Azure Blob Storage using the URL
    3. Call POST /{agreement_id}/pdf to confirm upload
    """
    # Verify base agreement exists
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    # Validate file extension
    allowed_extensions = ['.pdf', '.doc', '.docx']
    file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique blob name
    import uuid
    blob_name = f"{agreement_id}/{uuid.uuid4()}{file_ext}"
    
    try:
        result = storage_service.generate_upload_sas(
            container=BASE_AGREEMENT_CONTAINER,
            blob_name=blob_name,
            expiry_minutes=15
        )
        
        return {
            "url": result["url"],
            "blob_name": result["blob_name"],
            "container": BASE_AGREEMENT_CONTAINER,
            "expires_at": result["expires_at"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.post("/{agreement_id}/pdf", response_model=BaseAgreementResponse)
async def attach_pdf_to_agreement(
    agreement_id: str,
    body: BaseAgreementPdfUpload,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Attach an uploaded PDF to the base agreement.
    
    Call this after successfully uploading the PDF to Azure Blob Storage.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    # Delete old PDF if exists
    if base_agreement.pdf_blob_name:
        try:
            storage_service.delete_blob(
                container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
                blob_name=base_agreement.pdf_blob_name
            )
        except Exception:
            pass
    
    # Update with new PDF info
    base_agreement.pdf_container = body.container
    base_agreement.pdf_blob_name = body.blob_name
    base_agreement.pdf_filename = body.filename
    base_agreement.pdf_size_bytes = body.size_bytes
    
    db.commit()
    db.refresh(base_agreement)
    
    return _build_base_agreement_response(base_agreement)


@router.post("/{agreement_id}/upload-base64", response_model=FileUploadResponse)
async def upload_pdf_base64(
    agreement_id: str,
    body: Base64FileUpload,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Upload a PDF via base64 encoding.
    
    This is a simpler approach than the SAS token flow:
    1. Frontend converts file to base64
    2. Send base64 string in request body
    3. Backend decodes, saves, and returns URLs
    """
    import base64
    import uuid
    
    # Verify base agreement exists
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    # Validate file extension
    allowed_extensions = ['.pdf', '.doc', '.docx']
    file_ext = '.' + body.filename.split('.')[-1].lower() if '.' in body.filename else ''
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Decode base64 content
    try:
        # Handle data URL format (data:application/pdf;base64,...)
        content_base64 = body.content_base64
        if ',' in content_base64:
            content_base64 = content_base64.split(',')[1]
        
        file_content = base64.b64decode(content_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 content: {str(e)}"
        )
    
    # Generate unique blob name
    blob_name = f"{agreement_id}/{uuid.uuid4()}{file_ext}"
    
    # Delete old PDF if exists
    if base_agreement.pdf_blob_name:
        try:
            storage_service.delete_blob(
                container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
                blob_name=base_agreement.pdf_blob_name
            )
        except Exception:
            pass
    
    # Upload to storage
    try:
        storage_service.upload_blob(
            container=BASE_AGREEMENT_CONTAINER,
            blob_name=blob_name,
            data=file_content,
            content_type=body.content_type or "application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Update database with PDF info
    base_agreement.pdf_container = BASE_AGREEMENT_CONTAINER
    base_agreement.pdf_blob_name = blob_name
    base_agreement.pdf_filename = body.filename
    base_agreement.pdf_size_bytes = len(file_content)
    
    db.commit()
    db.refresh(base_agreement)
    
    # Generate download/preview URLs
    try:
        download_result = storage_service.generate_download_sas(
            container=BASE_AGREEMENT_CONTAINER,
            blob_name=blob_name,
            expiry_minutes=60
        )
        download_url = download_result["url"]
        preview_url = download_url  # Same URL can be used for preview
    except Exception:
        # Fallback to local URLs
        download_url = f"http://localhost:8000/api/local-download/{BASE_AGREEMENT_CONTAINER}/{blob_name}"
        preview_url = download_url
    
    return FileUploadResponse(
        success=True,
        filename=body.filename,
        size_bytes=len(file_content),
        download_url=download_url,
        preview_url=preview_url,
        blob_name=blob_name
    )


@router.delete("/{agreement_id}/pdf", response_model=BaseAgreementResponse)
async def remove_pdf_from_agreement(
    agreement_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Remove the PDF from a base agreement.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    if not base_agreement.pdf_blob_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PDF attached to this agreement"
        )
    
    # Delete from storage
    try:
        storage_service.delete_blob(
            container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
            blob_name=base_agreement.pdf_blob_name
        )
    except Exception:
        pass
    
    # Clear PDF fields
    base_agreement.pdf_container = None
    base_agreement.pdf_blob_name = None
    base_agreement.pdf_filename = None
    base_agreement.pdf_size_bytes = None
    
    db.commit()
    db.refresh(base_agreement)
    
    return _build_base_agreement_response(base_agreement)


@router.get("/{agreement_id}/pdf/download-sas")
async def get_pdf_download_sas(
    agreement_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a SAS token for downloading the PDF.
    
    Public endpoint - no auth required for viewing agreements.
    """
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    if not base_agreement.pdf_blob_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF attached to this agreement"
        )
    
    try:
        result = storage_service.generate_download_sas(
            container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
            blob_name=base_agreement.pdf_blob_name,
            expiry_minutes=60
        )
        
        return {
            "url": result["url"],
            "filename": base_agreement.pdf_filename,
            "size_bytes": base_agreement.pdf_size_bytes,
            "expires_at": result["expires_at"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/{agreement_id}/pdf")
async def serve_pdf(
    agreement_id: str,
    db: Session = Depends(get_db)
):
    """
    Serve the PDF directly or redirect to storage URL.
    
    For local storage: Returns the file directly
    For Azure storage: Redirects to signed URL
    """
    from fastapi.responses import RedirectResponse, FileResponse
    import os
    
    base_agreement = db.query(BaseAgreement).filter(
        BaseAgreement.id == agreement_id
    ).first()
    
    if not base_agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base agreement not found"
        )
    
    if not base_agreement.pdf_blob_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF attached to this agreement"
        )
    
    # Check if using local storage
    if storage_service.is_local:
        # Serve file directly from local storage
        from pathlib import Path
        base_path = Path(__file__).parent.parent.parent / "uploads"
        local_path = base_path / (base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER) / base_agreement.pdf_blob_name
        
        if local_path.exists():
            return FileResponse(
                str(local_path),
                media_type="application/pdf",
                filename=base_agreement.pdf_filename or "agreement.pdf"
            )
    
    # Fall back to redirect to signed URL
    try:
        result = storage_service.generate_download_sas(
            container=base_agreement.pdf_container or BASE_AGREEMENT_CONTAINER,
            blob_name=base_agreement.pdf_blob_name,
            expiry_minutes=60
        )
        return RedirectResponse(url=result["url"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve PDF: {str(e)}"
        )

