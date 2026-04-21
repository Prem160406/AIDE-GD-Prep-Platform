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