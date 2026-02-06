"""
Test the URL generation from local_storage service
"""
import sys
sys.path.insert(0, r"c:\python\room-mate-agreement-gen")

from app.services.local_storage import local_storage_service

# Test generate_upload_sas
result = local_storage_service.generate_upload_sas(
    container="base-agreements",
    blob_name="test-agreement-id/test-file.pdf"
)

print("Upload SAS Result:")
print(f"  URL: {result['url']}")
print(f"  blob_name: {result['blob_name']}")
print(f"  is_local: {result.get('is_local')}")
