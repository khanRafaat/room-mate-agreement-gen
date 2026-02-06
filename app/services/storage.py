"""
Roommate Agreement Generator - Storage Service
Azure Blob Storage integration with SAS token generation
Falls back to local storage in demo mode
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class StorageService:
    """Storage service - uses Azure Blob Storage or Local Storage based on config."""
    
    # Container names
    CONTAINER_AGREEMENTS = "agreements"
    CONTAINER_IDS = "ids"
    CONTAINER_SIGNED = "signed"
    CONTAINER_BASE_AGREEMENTS = "base-agreements"
    
    def __init__(self):
        """Initialize the storage service."""
        self._azure_client = None
        self._local_service = None
        self._use_local = False
        
        # Check if we should use local storage
        if settings.demo_mode or not settings.azure_storage_connection_string:
            self._use_local = True
    
    @property
    def is_local(self) -> bool:
        """Check if using local storage."""
        return self._use_local
    
    @property
    def local_service(self):
        """Get the local storage service."""
        if self._local_service is None:
            from app.services.local_storage import LocalStorageService
            self._local_service = LocalStorageService()
        return self._local_service
    
    @property
    def azure_client(self):
        """Get or create the Azure BlobServiceClient."""
        if self._use_local:
            raise ValueError("Using local storage, Azure client not available")
        
        if self._azure_client is None:
            from azure.storage.blob import BlobServiceClient
            if settings.azure_storage_connection_string:
                self._azure_client = BlobServiceClient.from_connection_string(
                    settings.azure_storage_connection_string
                )
            else:
                raise ValueError("Azure Storage connection string not configured")
        return self._azure_client
    
    @property
    def account_name(self) -> str:
        """Get the storage account name."""
        if self._use_local:
            return "localhost"
        return settings.azure_storage_account_name or self.azure_client.account_name
    
    def generate_upload_sas(
        self,
        container: str,
        blob_name: Optional[str] = None,
        expiry_minutes: int = 15
    ) -> dict:
        """
        Generate a SAS token for uploading a blob.
        """
        if self._use_local:
            return self.local_service.generate_upload_sas(container, blob_name, expiry_minutes)
        
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        if blob_name is None:
            blob_name = f"{uuid.uuid4()}"
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        token = generate_blob_sas(
            account_name=self.account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=settings.azure_storage_account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=expires_at
        )
        
        url = f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}?{token}"
        
        return {
            "url": url,
            "blob_name": blob_name,
            "expires_at": expires_at
        }
    
    def generate_download_sas(
        self,
        container: str,
        blob_name: str,
        expiry_minutes: int = 60
    ) -> dict:
        """
        Generate a SAS token for downloading a blob.
        """
        if self._use_local:
            return self.local_service.generate_download_sas(container, blob_name, expiry_minutes)
        
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        token = generate_blob_sas(
            account_name=self.account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=settings.azure_storage_account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expires_at
        )
        
        url = f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}?{token}"
        
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
        Upload data to a blob directly (server-side upload).
        """
        if self._use_local:
            return self.local_service.upload_blob(container, blob_name, data, content_type)
        
        from azure.storage.blob import ContentSettings
        
        blob_client = self.azure_client.get_blob_client(container=container, blob=blob_name)
        
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        return f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}"
    
    def download_blob(self, container: str, blob_name: str) -> bytes:
        """
        Download a blob's content.
        """
        if self._use_local:
            return self.local_service.download_blob(container, blob_name)
        
        blob_client = self.azure_client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()
    
    def delete_blob(self, container: str, blob_name: str) -> bool:
        """
        Delete a blob.
        """
        if self._use_local:
            return self.local_service.delete_blob(container, blob_name)
        
        blob_client = self.azure_client.get_blob_client(container=container, blob=blob_name)
        blob_client.delete_blob()
        return True
    
    def blob_exists(self, container: str, blob_name: str) -> bool:
        """
        Check if a blob exists.
        """
        if self._use_local:
            return self.local_service.blob_exists(container, blob_name)
        
        blob_client = self.azure_client.get_blob_client(container=container, blob=blob_name)
        return blob_client.exists()


# Singleton instance
storage_service = StorageService()

