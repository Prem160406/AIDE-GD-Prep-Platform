import requests
print("--- HR PLATFORM TEST SUITE RUNNING ---")

BASE = "http://127.0.0.1:5000"

print("\n1. Get Active Interviews/Trends")
# Shows what a student would see on the homepage
print(requests.get(f"{BASE}/api/gd-topics").json())

print("\n2. Get Specific Interview Set (ID=3)")
print(requests.get(f"{BASE}/api/gd-topics/3").json())

print("\n3. Get Admin Drafts")
# Shows topics Gopal needs to review
print(requests.get(f"{BASE}/api/admin/drafts").json())

print("\n4. Approve an Interview Set (ID=1)")
# Simulates Gopal saying "This AI generated set looks good!"
print(requests.post(f"{BASE}/api/admin/drafts/1/approve").json())

print("\n5. Reject an Interview Set (ID=2)")
# Simulates Gopal saying "This set is too generic, delete it."
print(requests.post(f"{BASE}/api/admin/drafts/2/reject").json())

print("\n6. Test AI Question Generation")
# Simulates a student typing a job role
response = requests.post(
    f"{BASE}/api/generate-questions",
    json={"text": "Full Stack Web Developer"}
)
print(response.json())

print("\n7. Test HR Trend Sync (RSS)")
# Simulates pulling latest hiring news from Glassdoor/Career blogs
sync_response = requests.post(f"{BASE}/api/admin/sync-trends", json={})

if sync_response.headers.get('Content-Type') == 'application/json':
    print(sync_response.json())
else:
    print(f"FAILED: Server returned {sync_response.status_code}")

print("\n8. Verify Final Draft Count")
drafts_response = requests.get(f"{BASE}/api/admin/drafts")
if drafts_response.status_code == 200:
    data = drafts_response.json().get('data', [])
    print(f"Total drafts in moderation: {len(data)}")