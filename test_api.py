import requests
print("TEST FILE RUNNING...")

BASE = "http://127.0.0.1:5000"

print("1. Get Active Topics")
print(requests.get(f"{BASE}/api/gd-topics").json())

print("\n2. Get Topic by ID")
print(requests.get(f"{BASE}/api/gd-topics/3").json())

print("\n3. Get Drafts")
print(requests.get(f"{BASE}/api/admin/drafts").json())

print("\n4. Approve Draft (ID=1)")
print(requests.post(f"{BASE}/api/admin/drafts/1/approve").json())

print("\n5. Reject Draft (ID=2)")
print(requests.post(f"{BASE}/api/admin/drafts/2/reject").json())


print("\n6. Test AI Analyze")
response = requests.post(
    f"{BASE}/api/analyze",
    json={"text": "AI is transforming jobs and industries rapidly"}
)
print(response.json())


print("\n7. Test RSS Sync")

sync_response = requests.post(f"{BASE}/api/admin/sync-news", json={})

# Check if the response is actually JSON before parsing
if sync_response.headers.get('Content-Type') == 'application/json':
    print(sync_response.json())
else:
    print(f"FAILED: Server returned {sync_response.status_code}")
    print("Check your Flask terminal for the red error traceback!")

print("\n8. Verify New Drafts from RSS")
drafts_response = requests.get(f"{BASE}/api/admin/drafts")
if drafts_response.status_code == 200:
    data = drafts_response.json().get('data', [])
    print(f"Total drafts now: {len(data)}")
else:
    print("Could not fetch drafts.")