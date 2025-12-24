"""
Roommate Agreement Generator - Files Router
API endpoints for file uploads and downloads via SAS tokens
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.deps.auth import get_current_user, CurrentUser
from app.models.models import AppUser, FileAsset
from app.schemas.file import SASRequest, SASResponse, UploadComplete, FileAssetResponse
from app.services.storage import storage_service

router = APIRouter(tags=["files"])


# Mapping of file kinds to containers
KIND_CONTAINER_MAP = {
    "lease_first_page": storage_service.CONTAINER_AGREEMENTS,
    "govt_id": storage_service.CONTAINER_IDS,
    "agreement_pdf": storage_service.CONTAINER_AGREEMENTS,
    "signed_pdf": storage_service.CONTAINER_SIGNED,
}


@router.post("/upload-sas", response_model=SASResponse)
async def get_upload_sas(
    body: SASRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a SAS token for uploading a file to Azure Blob Storage.
    """
    user = current_user.user
    
    if body.kind not in KIND_CONTAINER_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file kind: {body.kind}"
        )
    
    container = KIND_CONTAINER_MAP[body.kind]
    
    # Generate a unique blob name with user prefix
    import uuid
    file_ext = body.filename.split(".")[-1] if "." in body.filename else ""
    blob_name = f"{user.id}/{uuid.uuid4()}.{file_ext}" if file_ext else f"{user.id}/{uuid.uuid4()}"
    
    try:
        result = storage_service.generate_upload_sas(
            container=container,
            blob_name=blob_name,
            expiry_minutes=15
        )
        
        return SASResponse(
            url=result["url"],
            blob_name=result["blob_name"],
            expires_at=result["expires_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.post("/upload-complete", response_model=FileAssetResponse)
async def complete_upload(
    body: UploadComplete,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Record a completed file upload in the database.
    """
    user = current_user.user
    
    if body.kind not in KIND_CONTAINER_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file kind: {body.kind}"
        )
    
    # Create file asset record
    file_asset = FileAsset(
        owner_id=user.id,
        kind=body.kind,
        container=body.container,
        blob_name=body.blob_name,
        size_bytes=body.size_bytes
    )
    db.add(file_asset)
    db.commit()
    db.refresh(file_asset)
    
    return file_asset


@router.get("/files/{file_id}/sas", response_model=SASResponse)
async def get_download_sas(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a SAS token for downloading a file.
    """
    user = current_user.user
    
    file_asset = db.query(FileAsset).filter(FileAsset.id == str(file_id)).first()
    
    if not file_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check ownership
    if file_asset.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this file"
        )
    
    try:
        result = storage_service.generate_download_sas(
            container=file_asset.container,
            blob_name=file_asset.blob_name,
            expiry_minutes=60
        )
        
        return SASResponse(
            url=result["url"],
            blob_name=result["blob_name"],
            expires_at=result["expires_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/files", response_model=list[FileAssetResponse])
async def list_files(
    kind: str = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    List files owned by the current user.
    """
    user = current_user.user
    
    query = db.query(FileAsset).filter(FileAsset.owner_id == user.id)
    
    if kind:
        if kind not in KIND_CONTAINER_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file kind: {kind}"
            )
        query = query.filter(FileAsset.kind == kind)
    
    files = query.order_by(FileAsset.created_at.desc()).all()
    
    return files


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete a file (record and blob).
    """
    user = current_user.user
    
    file_asset = db.query(FileAsset).filter(FileAsset.id == str(file_id)).first()
    
    if not file_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check ownership
    if file_asset.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this file"
        )
    
    # Delete from storage (optional, depends on retention policy)
    try:
        storage_service.delete_blob(
            container=file_asset.container,
            blob_name=file_asset.blob_name
        )
    except Exception:
        pass  # Blob may already be deleted
    
    # Delete record
    db.delete(file_asset)
    db.commit()
    
    return None
