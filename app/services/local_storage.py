"""
Roommate Agreement Generator - Local Storage Service
Local file storage for demo mode when Azure is not configured
"""
import os
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import get_settings

settings = get_settings()


class LocalStorageService:
    """Local file storage service for demo mode."""
    
    # Container names (mapped to subdirectories)
    CONTAINER_AGREEMENTS = "agreements"
    CONTAINER_IDS = "ids"
    CONTAINER_SIGNED = "signed"
    CONTAINER_BASE_AGREEMENTS = "base-agreements"
    
    def __init__(self, base_path: str = None):
        """Initialize the local storage service."""
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to uploads folder in project root
            self.base_path = Path(__file__).parent.parent.parent / "uploads"
        
        # Create base directory if not exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_container_path(self, container: str) -> Path:
        """Get the path for a container (directory)."""
        container_path = self.base_path / container
        container_path.mkdir(parents=True, exist_ok=True)
        return container_path
    
    def _get_blob_path(self, container: str, blob_name: str) -> Path:
        """Get the full path for a blob."""
        container_path = self._get_container_path(container)
        # Handle nested blob names (e.g., "base-agreements/123/file.pdf")
        blob_path = container_path / blob_name
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        return blob_path
    
    def generate_upload_sas(
        self,
        container: str,
        blob_name: Optional[str] = None,
        expiry_minutes: int = 15
    ) -> dict:
        """
        Generate a "SAS token" for uploading - in local mode, 
        this returns a local endpoint URL.
        """
        if blob_name is None:
            blob_name = f"{uuid.uuid4()}"
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # In local mode, we use a direct upload endpoint
        # The URL points to our own API endpoint
        base_url = f"http://localhost:8000"
        url = f"{base_url}/api/local-upload/{container}/{blob_name}"
        
        return {
            "url": url,
            "blob_name": blob_name,
            "expires_at": expires_at,
            "is_local": True  # Flag to indicate local storage
        }
    
    def generate_download_sas(
        self,
        container: str,
        blob_name: str,
        expiry_minutes: int = 60
    ) -> dict:
        """
        Generate a download URL for local storage.
        """
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        base_url = f"http://localhost:8000"
        url = f"{base_url}/api/local-download/{container}/{blob_name}"
        
        return {
            "url": url,
            "blob_name": blob_name,
            "expires_at": expires_at
        }
    
    def upload_blob(
        self,
        container: str,
        blob_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload data to local storage.
        """
        blob_path = self._get_blob_path(container, blob_name)
        
        with open(blob_path, 'wb') as f:
            f.write(data)
        
        return f"/api/local-download/{container}/{blob_name}"
    
    def download_blob(self, container: str, blob_name: str) -> bytes:
        """
        Download a blob's content from local storage.
        """
        blob_path = self._get_blob_path(container, blob_name)
        
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {container}/{blob_name}")
        
        with open(blob_path, 'rb') as f:
            return f.read()
    
    def delete_blob(self, container: str, blob_name: str) -> bool:
        """
        Delete a blob from local storage.
        """
        blob_path = self._get_blob_path(container, blob_name)
        
        if blob_path.exists():
            os.remove(blob_path)
            return True
        return False
    
    def blob_exists(self, container: str, blob_name: str) -> bool:
        """
        Check if a blob exists in local storage.
        """
        blob_path = self._get_blob_path(container, blob_name)
        return blob_path.exists()
    
    def get_blob_path(self, container: str, blob_name: str) -> Path:
        """
        Get the actual file path for a blob (for serving).
        """
        return self._get_blob_path(container, blob_name)


# Singleton instance
local_storage_service = LocalStorageService()
