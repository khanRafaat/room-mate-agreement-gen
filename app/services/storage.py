"""
Roommate Agreement Generator - Storage Service
Azure Blob Storage integration with SAS token generation
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
    ContentSettings
)

from app.config import get_settings

settings = get_settings()


class StorageService:
    """Azure Blob Storage service for file management."""
    
    # Container names
    CONTAINER_AGREEMENTS = "agreements"
    CONTAINER_IDS = "ids"
    CONTAINER_SIGNED = "signed"
    
    def __init__(self):
        """Initialize the storage service."""
        self._client: Optional[BlobServiceClient] = None
    
    @property
    def client(self) -> BlobServiceClient:
        """Get or create the BlobServiceClient."""
        if self._client is None:
            if settings.azure_storage_connection_string:
                self._client = BlobServiceClient.from_connection_string(
                    settings.azure_storage_connection_string
                )
            else:
                raise ValueError("Azure Storage connection string not configured")
        return self._client
    
    @property
    def account_name(self) -> str:
        """Get the storage account name."""
        return settings.azure_storage_account_name or self.client.account_name
    
    def generate_upload_sas(
        self,
        container: str,
        blob_name: Optional[str] = None,
        expiry_minutes: int = 15
    ) -> dict:
        """
        Generate a SAS token for uploading a blob.
        
        Args:
            container: Container name
            blob_name: Optional blob name (generated if not provided)
            expiry_minutes: Token expiry in minutes
            
        Returns:
            Dict with url, blob_name, and expires_at
        """
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
        
        Args:
            container: Container name
            blob_name: Blob name
            expiry_minutes: Token expiry in minutes
            
        Returns:
            Dict with url, blob_name, and expires_at
        """
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
        
        Args:
            container: Container name
            blob_name: Blob name
            data: Bytes to upload
            content_type: Content type of the blob
            
        Returns:
            Blob URL
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        return f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}"
    
    def download_blob(self, container: str, blob_name: str) -> bytes:
        """
        Download a blob's content.
        
        Args:
            container: Container name
            blob_name: Blob name
            
        Returns:
            Blob content as bytes
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()
    
    def delete_blob(self, container: str, blob_name: str) -> bool:
        """
        Delete a blob.
        
        Args:
            container: Container name
            blob_name: Blob name
            
        Returns:
            True if deleted successfully
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        blob_client.delete_blob()
        return True
    
    def blob_exists(self, container: str, blob_name: str) -> bool:
        """
        Check if a blob exists.
        
        Args:
            container: Container name
            blob_name: Blob name
            
        Returns:
            True if blob exists
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        return blob_client.exists()


# Singleton instance
storage_service = StorageService()
