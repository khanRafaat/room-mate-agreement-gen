"""
Test the local-upload endpoint directly
"""
import requests

# Test if the endpoint exists
print("Testing local-upload endpoint...")

# First, let's just check what endpoints are available
try:
    resp = requests.get("http://localhost:8000/openapi.json")
    data = resp.json()
    
    # Find all paths that contain "local"
    paths = data.get("paths", {})
    local_paths = [p for p in paths.keys() if "local" in p.lower()]
    print(f"\nLocal endpoints found: {local_paths}")
    
    # Print the methods for each local path
    for path in local_paths:
        methods = list(paths[path].keys())
        print(f"  {path}: {methods}")
except Exception as e:
    print(f"Error: {e}")

# Try to upload a test file
print("\n\nTesting file upload...")
try:
    # Create a simple test file
    test_content = b"Test PDF content"
    files = {'file': ('test.pdf', test_content, 'application/pdf')}
    
    # Try the endpoint
    url = "http://localhost:8000/api/local-upload/base-agreements/test-file.pdf"
    print(f"URL: {url}")
    
    resp = requests.post(url, files=files)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Upload Error: {e}")
