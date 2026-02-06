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


# ==================== LOCAL FILE ENDPOINTS (Demo Mode) ====================

from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path


@router.put("/local-upload/{container}/{blob_name:path}")
async def local_upload_file(
    container: str,
    blob_name: str,
    file: UploadFile = File(...)
):
    """
    Direct file upload endpoint for local storage (demo mode).
    
    This endpoint is used when Azure storage is not configured.
    The frontend should upload files directly to this endpoint.
    """
    if not storage_service.is_local:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local upload not available - Azure storage is configured"
        )
    
    # Read file content
    content = await file.read()
    
    # Upload to local storage
    storage_service.upload_blob(
        container=container,
        blob_name=blob_name,
        data=content,
        content_type=file.content_type or "application/octet-stream"
    )
    
    return {"success": True, "blob_name": blob_name, "size_bytes": len(content)}


@router.post("/local-upload/{container}/{blob_name:path}")
async def local_upload_file_post(
    container: str,
    blob_name: str,
    file: UploadFile = File(...)
):
    """
    Direct file upload endpoint (POST variant) for local storage.
    """
    return await local_upload_file(container, blob_name, file)


@router.get("/local-download/{container}/{blob_name:path}")
async def local_download_file(
    container: str,
    blob_name: str
):
    """
    Direct file download endpoint for local storage (demo mode).
    
    Returns the file for download.
    """
    if not storage_service.is_local:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local download not available - Azure storage is configured"
        )
    
    # Get the file path
    from app.services.local_storage import local_storage_service
    file_path = local_storage_service.get_blob_path(container, blob_name)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine content type based on extension
    content_type_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
    }
    
    suffix = file_path.suffix.lower()
    content_type = content_type_map.get(suffix, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=file_path.name
    )

