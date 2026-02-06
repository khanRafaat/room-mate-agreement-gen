"""
End-to-end test for base64 upload flow
"""
import sys
sys.path.insert(0, r"c:\python\room-mate-agreement-gen")

import base64
import requests

# Test the entire base64 upload flow
print("Testing base64 upload flow...")

# First, login to get a token
login_url = "http://localhost:8000/api/auth/login"
login_data = {"email": "admin@example.com", "password": "Admin@123"}

print("\n1. Logging in...")
try:
    resp = requests.post(login_url, data=login_data)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"   Login successful, got token")
    else:
        print(f"   Login failed: {resp.status_code} - {resp.text[:200]}")
        token = None
except Exception as e:
    print(f"   Login error: {e}")
    token = None

if not token:
    print("\n   Trying without auth for testing...")

# 2. Create a base agreement
print("\n2. Creating base agreement...")
headers = {"Authorization": f"Bearer {token}"} if token else {}

create_url = "http://localhost:8000/api/base-agreements"
create_data = {
    "city_id": "custom-test-city",
    "city_name": "Test City",
    "title": "Test Agreement",
    "content": "Test content",
    "applicable_for": "both"
}

try:
    resp = requests.post(create_url, json=create_data, headers=headers)
    if resp.status_code in [200, 201]:
        agreement_id = resp.json().get("id")
        print(f"   Created agreement: {agreement_id}")
    else:
        print(f"   Create failed: {resp.status_code} - {resp.text[:300]}")
        agreement_id = None
except Exception as e:
    print(f"   Create error: {e}")
    agreement_id = None

if not agreement_id:
    print("   Cannot continue without agreement ID")
    exit(1)

# 3. Upload a PDF via base64
print("\n3. Uploading PDF via base64...")
upload_url = f"http://localhost:8000/api/base-agreements/{agreement_id}/upload-base64"

# Create a simple test PDF content (just bytes for testing)
test_content = b"%PDF-1.4\nTest PDF content for upload testing\n%%EOF"
base64_content = base64.b64encode(test_content).decode('utf-8')

upload_data = {
    "filename": "test-agreement.pdf",
    "content_base64": base64_content,
    "content_type": "application/pdf"
}

try:
    resp = requests.post(upload_url, json=upload_data, headers=headers)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Filename: {result.get('filename')}")
        print(f"   Size: {result.get('size_bytes')} bytes")
        print(f"   Download URL: {result.get('download_url')}")
        print(f"   Preview URL: {result.get('preview_url')}")
        print(f"   Blob name: {result.get('blob_name')}")
    else:
        print(f"   Upload failed: {resp.text[:500]}")
except Exception as e:
    print(f"   Upload error: {e}")

print("\n4. Test complete!")
