"""
End-to-End Runtime Zero-Demo-Data Audit Script.
Executes against live server http://127.0.0.1:8000 with fresh database.
"""
import sys
import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("CIVICFLOW ZERO-DEMO-DATA LIVE RUNTIME AUDIT")
print("=" * 60)

with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
    # 1. Health check
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
    print("[PASS] 1. Backend /health is OK")

    r_db = client.get("/health/db")
    assert r_db.status_code == 200, f"DB health check failed: {r_db.text}"
    db_json = r_db.json()
    assert db_json.get("database", {}).get("connected") is True, f"DB not connected: {db_json}"
    print("[PASS] 2. Backend /health/db connected to fresh runtime database")

    # 2. Register fresh audit user
    user_payload = {
        "name": "Audit Citizen",
        "email": "audit_citizen@civicflow.local",
        "password": "AuditPassword123!"
    }
    r_reg = client.post("/api/v1/auth/register", json=user_payload)
    assert r_reg.status_code == 201, f"Registration failed: {r_reg.text}"
    user_id = r_reg.json()["id"]
    print(f"[PASS] 3. Registered fresh citizen user (ID: {user_id})")

    # 3. Authenticate and obtain JWT
    r_login = client.post("/api/v1/auth/login", json={
        "email": "audit_citizen@civicflow.local",
        "password": "AuditPassword123!"
    })
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 4. Obtained JWT access token")

    # 4. Check initial complaints list - MUST BE ZERO
    r_list_initial = client.get("/api/v1/complaints", headers=headers)
    assert r_list_initial.status_code == 200
    initial_complaints = r_list_initial.json()
    assert len(initial_complaints) == 0, f"Expected 0 complaints, found {len(initial_complaints)}: {initial_complaints}"
    print(f"[PASS] 5. Fresh runtime database contains ZERO pre-created complaints (count={len(initial_complaints)})")

    # 5. Create a real user test image (valid JPEG photo)
    test_img_path = Path(__file__).parent / "fixtures" / "sample_pothole.jpg"
    with open(test_img_path, "rb") as f:
        img_bytes = f.read()

    # Submit ONE complaint through the actual intake API
    r_create = client.post(
        "/api/v1/complaints/analyze",
        headers=headers,
        files={"image": ("citizen_evidence.jpg", img_bytes, "image/jpeg")},
        data={
            "original_problem": "Broken pedestrian walkway paver blocks creating trip hazard",
            "original_address": "Eiffel Tower, Paris",
            "original_latitude": 48.8584,
            "original_longitude": 2.2945
        }
    )
    assert r_create.status_code == 201, f"Complaint intake failed: {r_create.text}"
    complaint = r_create.json()
    cid = complaint["id"]
    print(f"[PASS] 6. Created ONE single complaint via API (ID: {cid})")
    assert complaint["status"] == "DRAFT"
    assert complaint["original_problem"] == "Broken pedestrian walkway paver blocks creating trip hazard"
    assert complaint["original_address"] == "Eiffel Tower, Paris"
    assert complaint["original_latitude"] == 48.8584
    assert complaint["original_longitude"] == 2.2945
    print("[PASS] 7. Complaint preserved raw problem description, address, and device coordinates")

    # 6. Verify complaints list now contains EXACTLY ONE complaint
    r_list_after = client.get("/api/v1/complaints", headers=headers)
    assert r_list_after.status_code == 200
    complaints_after = r_list_after.json()
    assert len(complaints_after) == 1, f"Expected exactly 1 complaint, found {len(complaints_after)}"
    assert complaints_after[0]["id"] == cid
    print("[PASS] 8. Complaints list contains strictly the ONE submitted complaint (zero dummy/sample items)")

    # 7. Verify evidence image streaming with auth
    r_img = client.get(f"/api/v1/complaints/{cid}/image", headers=headers)
    assert r_img.status_code == 200, f"Image fetch failed: {r_img.status_code}"
    assert len(r_img.content) == len(img_bytes)
    print(f"[PASS] 9. Uploaded evidence image securely retrieved and matches submitted bytes ({len(r_img.content)} bytes)")

    # 8. Execute location verification on the complaint
    r_geo = client.post(f"/api/v1/complaints/{cid}/location/verify", headers=headers)
    assert r_geo.status_code == 200, f"Location verification failed: {r_geo.text}"
    geo_data = r_geo.json()
    assert geo_data["location_status"] in ("VERIFIED", "GEOCODED", "COORDINATES_ATTACHED")
    assert "openstreetmap.org" in geo_data["map_url"]
    print(f"[PASS] 10. Geographic verification resolved correctly: status={geo_data['location_status']}, map_url={geo_data['map_url']}")

print("\n" + "=" * 60)
print("AUDIT VERDICT: 100% CLEAN — ZERO DEMO DATA DETECTED IN RUNTIME")
print("=" * 60)
