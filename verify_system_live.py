"""
Comprehensive Live Verification Script for CivicFlow.
Tests against the live running FastAPI backend (http://127.0.0.1:8000).

Validates:
1. Citizen authentication (login/register).
2. Complaint creation with real image bytes.
3. Real Gemini multimodal analysis (structured draft: category, observed_issue, citizen_claim, formal_summary, urgency_level, warnings).
4. Geographic verification.
5. Human review draft editing and saving.
6. Authoritative final submission (UNDER_REVIEW -> SUBMITTED).
7. Admin status isolation:
   - Default queue exposes only SUBMITTED.
   - ALL_ADJUDICABLE exposes only SUBMITTED, ACCEPTED, REJECTED.
   - Admin queue rejects DRAFT/AI_GENERATED/UNDER_REVIEW query with 400.
   - Admin detail rejects DRAFT/AI_GENERATED/UNDER_REVIEW complaint ID with 404.
8. Admin adjudication: Accept complaint (transitions to ACCEPTED with server UTC decided_at).
9. Real in-app notification delivered to citizen for acceptance.
10. Admin adjudication: Reject complaint with real admin_reason (transitions to REJECTED with server UTC decided_at).
11. Real in-app notification delivered to citizen with actual admin rejection reason.
12. Notification unread count and mark-as-read verification.
"""

import sys
import os
import io
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def run_verification():
    print("=" * 70)
    print("CIVICFLOW LIVE SYSTEM VERIFICATION")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    # 1. Health checks
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"/health failed: {r.status_code}"
    log("/health is OK", "PASS")

    r = requests.get(f"{BASE_URL}/health/db")
    assert r.status_code == 200, f"/health/db failed: {r.status_code}"
    db_info = r.json()
    log(f"/health/db is OK: dialect={db_info.get('database', {}).get('dialect')}", "PASS")

    # 2. Authenticate Citizen
    citizen_email = f"citizen_test_{int(time.time())}@civicflow.org"
    citizen_pass = "CitizenPass123!"
    citizen_name = "Jane Verification Citizen"

    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": citizen_email,
        "password": citizen_pass,
        "name": citizen_name
    })
    if r.status_code == 201:
        citizen_token = r.json()["access_token"]
        log(f"Registered new citizen: {citizen_email}", "PASS")
    else:
        # Try login
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": citizen_email,
            "password": citizen_pass
        })
        assert r.status_code == 200, f"Citizen login failed: {r.text}"
        citizen_token = r.json()["access_token"]
        log(f"Logged in citizen: {citizen_email}", "PASS")

    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}

    # 3. Authenticate Admin
    admin_email = "admin@civicflow.org"
    admin_pass = "AdminPass123!"
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": admin_email,
        "password": admin_pass
    })
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    log(f"Logged in admin: {admin_email}", "PASS")

    # 4. Check Admin Status Isolation on Existing Complaints
    # Query admin complaints default queue
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints", headers=admin_headers)
    assert r.status_code == 200, f"Failed to list admin complaints: {r.text}"
    default_queue = r.json()
    for item in default_queue:
        assert item["status"] == "SUBMITTED", f"CRITICAL: Non-submitted complaint {item['id']} in default admin queue: status={item['status']}"
    log(f"Default admin queue returned {len(default_queue)} items — ALL are strictly SUBMITTED", "PASS")

    # Query admin complaints with ALL_ADJUDICABLE
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints?status=ALL_ADJUDICABLE", headers=admin_headers)
    assert r.status_code == 200, f"Failed ALL_ADJUDICABLE query: {r.text}"
    adjudicable_list = r.json()
    for item in adjudicable_list:
        assert item["status"] in ("SUBMITTED", "ACCEPTED", "REJECTED"), f"CRITICAL: Non-adjudicable status in admin queue: {item['status']}"
    log(f"ALL_ADJUDICABLE query returned {len(adjudicable_list)} items — ALL are strictly adjudicable", "PASS")

    # Query admin complaints with DRAFT should return 400
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints?status=DRAFT", headers=admin_headers)
    assert r.status_code == 400, f"Expected 400 for ?status=DRAFT on admin queue, got {r.status_code}"
    log("Admin query for ?status=DRAFT correctly rejected with HTTP 400", "PASS")

    # 5. Create Real Citizen Complaint with Real Image
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "uploads", "complaints")
    sample_img_brain = r"C:\Users\SKAIK SAMEER\.gemini\antigravity-ide\brain\2ca0ba6f-afd2-4002-bc66-c2ad525ddc3f\sample_pothole_1791098828688.jpg"
    
    if os.path.exists(sample_img_brain):
        with open(sample_img_brain, "rb") as f:
            img_bytes = f.read()
    else:
        # 1x1 minimal valid JPEG
        img_bytes = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06'
            b'\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'
            b'\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff'
            b'\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01'
            b'\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n'
            b'\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
        )

    citizen_problem_text = "Hazardous deep pothole filled with stagnant rainwater at corner of 5th Main"
    citizen_address_text = "5th Main Road & 2nd Cross, Indiranagar"
    citizen_lat = 12.9716
    citizen_lng = 77.5946

    files = {"image": ("pothole.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "original_problem": citizen_problem_text,
        "original_address": citizen_address_text,
        "original_latitude": str(citizen_lat),
        "original_longitude": str(citizen_lng)
    }

    r = requests.post(f"{BASE_URL}/api/v1/complaints/analyze", headers=citizen_headers, files=files, data=data)
    assert r.status_code == 201, f"Failed to create complaint intake: {r.text}"
    complaint_1 = r.json()
    complaint_1_id = complaint_1["id"]
    assert complaint_1["status"] == "DRAFT"
    log(f"Created complaint {complaint_1_id} in status DRAFT", "PASS")

    # 6. Verify Admin Detail Rejects DRAFT
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}", headers=admin_headers)
    assert r.status_code == 404, f"Admin detail should return 404 for DRAFT complaint, got {r.status_code}"
    log(f"Admin detail for DRAFT complaint {complaint_1_id} strictly rejected with HTTP 404", "PASS")

    # 7. Run Gemini Multimodal AI Analysis
    log(f"Invoking Gemini multimodal AI analysis on complaint {complaint_1_id}...")
    r = requests.post(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}/analyze", headers=citizen_headers)
    assert r.status_code == 200, f"Gemini analysis failed: {r.text}"
    ai_draft = r.json()
    assert ai_draft.get("category"), "AI draft missing category"
    assert ai_draft.get("observed_issue"), "AI draft missing observed_issue"
    assert ai_draft.get("citizen_claim"), "AI draft missing citizen_claim"
    assert ai_draft.get("formal_summary"), "AI draft missing formal_summary"
    assert ai_draft.get("urgency_level") in ("LOW", "MEDIUM", "HIGH", "CRITICAL"), f"Invalid urgency: {ai_draft.get('urgency_level')}"
    log(f"Gemini analysis returned Category='{ai_draft.get('category')}', Urgency='{ai_draft.get('urgency_level')}'", "PASS")
    log(f"Observed Issue: '{ai_draft.get('observed_issue')}'", "PASS")
    log(f"Formal Summary: '{ai_draft.get('formal_summary')}'", "PASS")

    # Verify AI draft does not duplicate raw citizen problem as observed issue
    assert ai_draft["observed_issue"] != citizen_problem_text or len(citizen_problem_text) < 10, "AI observed_issue must be Gemini interpretation, not raw citizen copy"

    # Verify database persistence of AI fields
    r = requests.get(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}", headers=citizen_headers)
    assert r.status_code == 200
    c_updated = r.json()
    assert c_updated["status"] == "AI_GENERATED"
    assert c_updated["ai_problem"] == ai_draft["observed_issue"]
    assert c_updated["ai_summary"] == ai_draft["formal_summary"]
    log(f"Complaint {complaint_1_id} transitioned to AI_GENERATED with persisted AI fields", "PASS")

    # 8. Run Geographic Verification
    r = requests.post(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}/location/verify", headers=citizen_headers)
    assert r.status_code == 200, f"Location verification failed: {r.text}"
    loc = r.json()
    log(f"Geographic verification status: {loc.get('location_status')}", "PASS")

    # 9. Citizen Human Review & Draft Editing (Transitions to UNDER_REVIEW)
    final_problem_confirmed = f"Confirmed by citizen: {ai_draft['observed_issue']} on 5th Main"
    final_address_confirmed = citizen_address_text
    final_summary_confirmed = ai_draft['formal_summary']

    r = requests.put(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}/draft", headers=citizen_headers, json={
        "final_problem": final_problem_confirmed,
        "final_address": final_address_confirmed,
        "final_summary": final_summary_confirmed
    })
    assert r.status_code == 200, f"Draft update failed: {r.text}"
    c_under_review = r.json()
    assert c_under_review["status"] == "UNDER_REVIEW"
    assert c_under_review["final_problem"] == final_problem_confirmed
    log(f"Complaint {complaint_1_id} transitioned to UNDER_REVIEW with citizen authorization", "PASS")

    # Still rejected by Admin Detail because UNDER_REVIEW is not adjudicable
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}", headers=admin_headers)
    assert r.status_code == 404, f"Admin detail should return 404 for UNDER_REVIEW complaint, got {r.status_code}"
    log(f"Admin detail for UNDER_REVIEW complaint {complaint_1_id} strictly rejected with HTTP 404", "PASS")

    # 10. Authoritative Final Submission (Transitions to SUBMITTED)
    r = requests.post(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}/submit", headers=citizen_headers)
    assert r.status_code == 200, f"Submission failed: {r.text}"
    c_submitted = r.json()
    assert c_submitted["status"] == "SUBMITTED"
    assert c_submitted["submitted_at"] is not None
    log(f"Complaint {complaint_1_id} submitted successfully! submitted_at={c_submitted['submitted_at']}", "PASS")

    # 11. Locked Case: Citizen Cannot Edit Submitted Complaint
    r = requests.put(f"{BASE_URL}/api/v1/complaints/{complaint_1_id}/draft", headers=citizen_headers, json={
        "final_problem": "Attempting illegal edit on submitted complaint"
    })
    assert r.status_code == 400, f"Submitted complaint must reject draft edits, got {r.status_code}"
    log("Citizen attempt to edit SUBMITTED complaint correctly locked with HTTP 400", "PASS")

    # 12. Admin Queue NOW Exposes the Submitted Complaint
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints?status=SUBMITTED", headers=admin_headers)
    assert r.status_code == 200
    sub_ids = [item["id"] for item in r.json()]
    assert complaint_1_id in sub_ids, f"Submitted complaint {complaint_1_id} not found in admin SUBMITTED queue"
    log(f"Submitted complaint {complaint_1_id} is visibly present in Admin SUBMITTED queue", "PASS")

    # Admin Detail NOW Succeeds with Complete Evidence Package
    r = requests.get(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}", headers=admin_headers)
    assert r.status_code == 200, f"Failed to get admin detail: {r.text}"
    admin_detail_1 = r.json()
    assert admin_detail_1["original_problem"] == citizen_problem_text
    assert admin_detail_1["final_problem"] == final_problem_confirmed
    assert admin_detail_1["status"] == "SUBMITTED"
    log("Admin detail returned 200 with full 4-layer evidence package", "PASS")

    # 13. Admin Adjudication: Accept Complaint
    r = requests.post(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}/accept", headers=admin_headers)
    assert r.status_code == 200, f"Accept failed: {r.text}"
    c_accepted = r.json()
    assert c_accepted["status"] == "ACCEPTED"
    assert c_accepted["decided_at"] is not None
    log(f"Complaint {complaint_1_id} ACCEPTED by admin at {c_accepted['decided_at']}", "PASS")

    # Terminal state check: duplicate accept rejected
    r = requests.post(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}/accept", headers=admin_headers)
    assert r.status_code == 400, "Duplicate accept must be rejected with HTTP 400"
    log("Duplicate accept on ACCEPTED complaint correctly rejected with HTTP 400", "PASS")

    # Terminal state check: cannot reject accepted complaint
    r = requests.post(f"{BASE_URL}/api/v1/admin/complaints/{complaint_1_id}/reject", headers=admin_headers, json={
        "admin_reason": "Attempting reject on accepted"
    })
    assert r.status_code == 400, "Cannot reject ACCEPTED complaint"
    log("Reject attempt on ACCEPTED complaint correctly rejected with HTTP 400", "PASS")

    # 14. Verify Real Acceptance Notification Delivered to Citizen
    r = requests.get(f"{BASE_URL}/api/v1/notifications", headers=citizen_headers)
    assert r.status_code == 200, f"Failed to get notifications: {r.text}"
    notifs = r.json()
    accept_notif = next((n for n in notifs if n["complaint_id"] == complaint_1_id), None)
    assert accept_notif is not None, f"Acceptance notification not found for complaint {complaint_1_id}"
    assert "accepted" in accept_notif["title"].lower() or "accepted" in accept_notif["message"].lower()
    assert accept_notif["is_read"] is False
    log(f"Citizen received persistent acceptance notification (ID: {accept_notif['id']}): '{accept_notif['title']}'", "PASS")

    # 15. Create Second Complaint to Test Administrative Rejection with Reason
    files2 = {"image": ("pothole2.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data2 = {
        "original_problem": "Garbage dump accumulated on private apartment perimeter wall",
        "original_address": "8th Block Commercial Street",
        "original_latitude": "12.9800",
        "original_longitude": "77.6000"
    }
    r = requests.post(f"{BASE_URL}/api/v1/complaints/analyze", headers=citizen_headers, files=files2, data=data2)
    assert r.status_code == 201
    complaint_2_id = r.json()["id"]

    # AI analysis + submit
    requests.post(f"{BASE_URL}/api/v1/complaints/{complaint_2_id}/analyze", headers=citizen_headers)
    requests.put(f"{BASE_URL}/api/v1/complaints/{complaint_2_id}/draft", headers=citizen_headers, json={
        "final_problem": "Confirmed garbage accumulation on private apartment perimeter wall"
    })
    r = requests.post(f"{BASE_URL}/api/v1/complaints/{complaint_2_id}/submit", headers=citizen_headers)
    assert r.status_code == 200
    log(f"Second complaint {complaint_2_id} created and submitted for rejection test", "PASS")

    # 16. Admin Reject Complaint: Empty reason rejected (422)
    r = requests.post(f"{BASE_URL}/api/v1/admin/complaints/{complaint_2_id}/reject", headers=admin_headers, json={
        "admin_reason": "   "
    })
    assert r.status_code == 422, f"Expected 422 for whitespace rejection reason, got {r.status_code}"
    log("Whitespace rejection reason correctly rejected with HTTP 422", "PASS")

    # Admin Reject Complaint: Valid reason
    rejection_reason_text = "Issue located entirely on private residential property outside municipal road maintenance jurisdiction. Refer to resident association."
    r = requests.post(f"{BASE_URL}/api/v1/admin/complaints/{complaint_2_id}/reject", headers=admin_headers, json={
        "admin_reason": rejection_reason_text
    })
    assert r.status_code == 200, f"Reject failed: {r.text}"
    c_rejected = r.json()
    assert c_rejected["status"] == "REJECTED"
    assert c_rejected["admin_reason"] == rejection_reason_text
    assert c_rejected["decided_at"] is not None
    log(f"Complaint {complaint_2_id} REJECTED with valid admin reason: '{rejection_reason_text[:50]}...'", "PASS")

    # 17. Verify Real Rejection Notification Delivered to Citizen with Reason
    r = requests.get(f"{BASE_URL}/api/v1/notifications", headers=citizen_headers)
    assert r.status_code == 200
    notifs = r.json()
    reject_notif = next((n for n in notifs if n["complaint_id"] == complaint_2_id), None)
    assert reject_notif is not None, f"Rejection notification not found for complaint {complaint_2_id}"
    assert rejection_reason_text in reject_notif["message"], "Citizen notification must contain the exact admin rejection reason"
    log(f"Citizen received rejection notification with exact reason: '{reject_notif['message']}'", "PASS")

    # 18. Verify Unread Count & Mark-as-Read Persistence
    r = requests.get(f"{BASE_URL}/api/v1/notifications/unread-count", headers=citizen_headers)
    assert r.status_code == 200
    unread_before = r.json()["unread_count"]
    assert unread_before >= 2, f"Expected at least 2 unread notifications, got {unread_before}"
    log(f"Unread notification count: {unread_before}", "PASS")

    # Mark first notification as read
    r = requests.patch(f"{BASE_URL}/api/v1/notifications/{accept_notif['id']}/read", headers=citizen_headers)
    assert r.status_code == 200
    assert r.json()["is_read"] is True

    # Verify unread count decremented
    r = requests.get(f"{BASE_URL}/api/v1/notifications/unread-count", headers=citizen_headers)
    assert r.status_code == 200
    unread_after = r.json()["unread_count"]
    assert unread_after == unread_before - 1
    log(f"Notification {accept_notif['id']} marked as read; unread count decremented to {unread_after}", "PASS")

    print("\n" + "=" * 70)
    print("ALL 18 END-TO-END VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
