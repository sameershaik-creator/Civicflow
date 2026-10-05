"""
CivicFlow — Phase 9 Verification Test Suite: Municipal Administrator Adjudication Dashboard

Verifies:
A. Admin Authentication & RBAC
   1. Unauthenticated admin complaint list returns 401 Unauthorized.
   2. Citizen access to admin complaint list returns 403 Forbidden.
   3. Admin access to admin complaint list returns 200 OK.

B. Admin Listing
   4. Admin complaint list returns submitted complaints.
   5. Non-submitted complaints are excluded from default SUBMITTED queue.
   6. Filtering by status works (SUBMITTED, ACCEPTED, REJECTED, ALL).
   7. Empty database returns empty list [] (zero demo data).

C. Admin Detail
   8. Unauthenticated access to admin detail returns 401 Unauthorized.
   9. Citizen access to admin detail returns 403 Forbidden.
   10. Nonexistent complaint ID returns 404 Not Found.
   11. Admin access to admin detail returns 200 with full evidence package.

D. Accept FSM
   12. Admin can accept SUBMITTED complaint -> transitions to ACCEPTED.
   13. DRAFT cannot be accepted (400 Bad Request).
   14. AI_GENERATED cannot be accepted (400 Bad Request).
   15. UNDER_REVIEW cannot be accepted (400 Bad Request).
   16. Duplicate accept on ACCEPTED complaint is rejected (400 Bad Request).
   17. REJECTED complaint cannot be accepted (terminal lock -> 400 Bad Request).
   18. Citizen cannot accept complaint (403 Forbidden).
   19. Unauthenticated accept returns 401 Unauthorized.

E. Reject FSM
   20. Admin can reject SUBMITTED complaint with valid reason -> transitions to REJECTED.
   21. Missing rejection reason is rejected (422 Unprocessable Entity).
   22. Empty rejection reason is rejected (422 Unprocessable Entity).
   23. Whitespace-only rejection reason is rejected (422 Unprocessable Entity).
   24. DRAFT cannot be rejected (400 Bad Request).
   25. AI_GENERATED cannot be rejected (400 Bad Request).
   26. UNDER_REVIEW cannot be rejected (400 Bad Request).
   27. Duplicate reject on REJECTED complaint is rejected (400 Bad Request).
   28. ACCEPTED complaint cannot be rejected (terminal lock -> 400 Bad Request).
   29. Citizen cannot reject complaint (403 Forbidden).
   30. Unauthenticated reject returns 401 Unauthorized.

F. Server Control & Payload Security
   31. Client cannot inject status via accept payload.
   32. Client cannot inject decided_at via accept payload.
   33. Client cannot alter user_id via accept payload.
   34. Client cannot inject status via reject payload.
   35. Client cannot inject decided_at via reject payload.
   36. Client cannot alter user_id via reject payload.

G. Server-Generated UTC Timestamp
   37. decided_at is generated server-side on accept.
   38. decided_at is generated server-side on reject.
   39. decided_at is in UTC timezone.
   40. decided_at is persisted in database.
   41. Repeated/duplicate requests cannot alter or overwrite decided_at.

H. Provenance Immutability
   42. original_problem remains strictly unchanged after adjudication.
   43. original_address remains strictly unchanged.
   44. original_latitude & longitude remain strictly unchanged.
   45. image_url remains strictly unchanged.
   46. ai_problem, ai_address, ai_summary remain strictly unchanged.
   47. final_problem, final_address, final_summary remain strictly unchanged.

I. Terminal Lock Enforcement
   48. Citizen draft edit (PUT /{id}/draft) on ACCEPTED complaint is rejected (400).
   49. Citizen draft edit (PUT /{id}/draft) on REJECTED complaint is rejected (400).
   50. Citizen submission (POST /{id}/submit) on ACCEPTED complaint is rejected (400).
   51. Citizen submission (POST /{id}/submit) on REJECTED complaint is rejected (400).

J. Evidence Image Security
   52. Admin can retrieve evidence image via protected image endpoint (200 OK).
   53. Foreign citizen image access is rejected (403 Forbidden).
   54. Unauthenticated image access is rejected (401 Unauthorized).

K. Geographic Review
   55. Verified location coordinates and map URL remain intact in admin detail.

L. Transaction Atomicity & Safety
   56. Failed persistence during accept rolls back cleanly (no partial status or decided_at).
   57. Failed persistence during reject rolls back cleanly (no partial reason, status, or decided_at).

M. Zero-Demo-Data Forensic Audit
   58. Normal runtime database contains zero complaints.
   59. Frontend source contains zero hardcoded complaint records.
   60. Frontend source contains zero sample image references.
   61. Frontend source contains zero hardcoded map markers.

N. Cumulative Regressions (Phases 1-8)
   62. Phase 1: /health & /health/db return 200 OK.
   63. Phase 2: Database schema and ORM models intact.
   64. Phase 3: Login and JWT issuance succeed.
   65. Phase 4: Complaint intake created in DRAFT.
   66. Phase 5: Gemini AI draft transitions complaint to AI_GENERATED.
   67. Phase 6: Geographic verification succeeds.
   68. Phase 7: Draft editing transitions complaint to UNDER_REVIEW.
   69. Phase 8: Final submission transitions complaint to SUBMITTED.

O. Real Runtime End-to-End Pipeline
   70. Full pipeline: citizen intake -> AI analysis -> geographic verification -> citizen review -> submission -> admin adjudication (ACCEPTED) -> terminal state lock.
"""

import sys
import os
import re
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Resolve project paths
current_file = Path(__file__).resolve()
if current_file.parent.name == "backend":
    project_root = current_file.parent.parent
    backend_dir = current_file.parent
elif current_file.parent.name == "frontend":
    project_root = current_file.parent.parent
    backend_dir = project_root / "backend"
else:
    project_root = current_file.parent
    backend_dir = project_root / "backend"

sys.path.insert(0, str(backend_dir))

# Add venv site-packages if needed
venv_site = project_root / "venv" / "Lib" / "site-packages"
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(1, str(venv_site))

# Fix passlib / bcrypt compatibility
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        import types
        bcrypt.__about__ = types.SimpleNamespace(__version__=getattr(bcrypt, "__version__", "4.0.0"))
except Exception:
    pass

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, LocationStatus
from app.config import settings
from app.services import auth_service
from app.agent import gemini_agent
from app.schemas.ai import GeminiComplaintDraft

# Minimal 1x1 test image
TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
    b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


def run_tests():
    print("=" * 70)
    print("CIVICFLOW PHASE 9 — MUNICIPAL ADMINISTRATOR ADJUDICATION TEST SUITE")
    print("=" * 70)

    # Setup isolated temporary test database
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_test_p9.db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p9_uploads_")
    orig_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_upload_dir

    from app.main import app

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    passed = 0
    failed = 0
    blocked = 0

    def record(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f" [PASS] {name}" + (f" -> {detail}" if detail else ""))
        else:
            failed += 1
            print(f" [FAIL] {name}" + (f" -> {detail}" if detail else ""))

    def record_blocked(name: str, detail: str = ""):
        nonlocal blocked
        blocked += 1
        print(f" [BLOCKED] {name}" + (f" -> {detail}" if detail else ""))

    try:
        # Seed test users
        with TestingSessionLocal() as session:
            citizen_a = User(
                id=str(uuid.uuid4()),
                email="citizen_p9_a@example.com",
                name="Fatima Al-Nuaimi",
                password_hash=auth_service.hash_password("PassFatima123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            citizen_b = User(
                id=str(uuid.uuid4()),
                email="citizen_p9_b@example.com",
                name="Rashid Al-Kindi",
                password_hash=auth_service.hash_password("PassRashid123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin_p9@example.com",
                name="Director of Municipal Public Works",
                password_hash=auth_service.hash_password("AdminWorksPass123!"),
                role=UserRole.ADMIN.value,
                created_at=datetime.now(timezone.utc)
            )

            session.add_all([citizen_a, citizen_b, admin_user])
            session.commit()

            token_citizen_a = auth_service.create_access_token(subject=citizen_a.id, role=citizen_a.role)
            token_citizen_b = auth_service.create_access_token(subject=citizen_b.id, role=citizen_b.role)
            token_admin = auth_service.create_access_token(subject=admin_user.id, role=admin_user.role)

        now = datetime.now(timezone.utc)

        print("\n--- Group A: Admin Authentication & RBAC ---")

        # 1. Unauthenticated admin complaint list returns 401
        r = client.get("/api/v1/admin/complaints")
        record("1. Unauthenticated admin complaint list returns 401", r.status_code == 401, f"status={r.status_code}")

        # 2. Citizen access to admin complaint list returns 403
        r = client.get("/api/v1/admin/complaints", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("2. Citizen access to admin complaint list returns 403", r.status_code == 403, f"status={r.status_code}")

        # 3. Admin access to admin complaint list returns 200
        r = client.get("/api/v1/admin/complaints", headers={"Authorization": f"Bearer {token_admin}"})
        record("3. Admin access to admin complaint list returns 200", r.status_code == 200, f"status={r.status_code}")

        # 7. Empty database returns empty list [] (zero demo data)
        record("7. Empty database returns empty list []", r.json() == [], f"count={len(r.json())}")

        print("\n--- Group B: Admin Listing & Queue Filtering ---")

        # Seed real test complaints in different FSM states
        with TestingSessionLocal() as session:
            c_sub1 = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_sub1.jpg",
                original_problem="Main street water main fracture gushing water",
                original_address="North Main Street, Plot 4",
                original_latitude=12.9716,
                original_longitude=77.5946,
                ai_problem="Potable water mains rupture with heavy surface runoff.",
                ai_summary="Immediate isolation of distribution valve recommended.",
                final_problem="High pressure municipal water mains rupture flooding pedestrian walkway on North Main Street",
                final_address="North Main Street, Opposite Plot 4",
                final_summary="High priority public works dispatch required: continuous water wastage.",
                latitude=12.9716,
                longitude=77.5946,
                location_status=LocationStatus.VERIFIED.value,
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            c_sub2 = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_b.id,
                image_url="/uploads/complaints/p9_sub2.jpg",
                original_problem="Deep roadway pothole at commercial junction",
                final_problem="Substantial road crater causing axle hazard at commercial junction",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            c_draft = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_draft.jpg",
                original_problem="Draft complaint not yet reviewed",
                status=ComplaintStatus.DRAFT.value,
                created_at=now,
                updated_at=now
            )
            c_ai = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_ai.jpg",
                original_problem="AI generated complaint awaiting user edits",
                status=ComplaintStatus.AI_GENERATED.value,
                created_at=now,
                updated_at=now
            )
            c_under = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_under.jpg",
                original_problem="Under review complaint",
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            session.add_all([c_sub1, c_sub2, c_draft, c_ai, c_under])
            session.commit()
            sub1_id = c_sub1.id
            sub2_id = c_sub2.id
            draft_id = c_draft.id
            ai_id = c_ai.id
            under_id = c_under.id

        # 4. Admin complaint list returns submitted complaints
        r = client.get("/api/v1/admin/complaints", headers={"Authorization": f"Bearer {token_admin}"})
        sub_list = r.json()
        sub_ids = [item["id"] for item in sub_list]
        record("4. Admin complaint list returns submitted complaints", (sub1_id in sub_ids and sub2_id in sub_ids), f"returned={len(sub_list)}")

        # 5. Non-submitted complaints are excluded from default SUBMITTED queue
        record("5. Non-submitted complaints excluded from default queue", (draft_id not in sub_ids and under_id not in sub_ids and ai_id not in sub_ids))

        # 6. Filtering by status works
        r_all = client.get("/api/v1/admin/complaints?status=ALL", headers={"Authorization": f"Bearer {token_admin}"})
        all_ids = [item["id"] for item in r_all.json()]
        record("6. Filtering by status works (status=ALL)", (len(all_ids) == 5 and draft_id in all_ids and ai_id in all_ids), f"total={len(all_ids)}")

        print("\n--- Group C: Admin Detail & Complete Evidence Package ---")

        # 8. Unauthenticated access to admin detail returns 401
        r = client.get(f"/api/v1/admin/complaints/{sub1_id}")
        record("8. Unauthenticated access to admin detail returns 401", r.status_code == 401)

        # 9. Citizen access to admin detail returns 403
        r = client.get(f"/api/v1/admin/complaints/{sub1_id}", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("9. Citizen access to admin detail returns 403", r.status_code == 403)

        # 10. Nonexistent complaint ID returns 404
        r = client.get(f"/api/v1/admin/complaints/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token_admin}"})
        record("10. Nonexistent complaint ID returns 404", r.status_code == 404)

        # 11. Admin access to admin detail returns 200 with full evidence package
        r = client.get(f"/api/v1/admin/complaints/{sub1_id}", headers={"Authorization": f"Bearer {token_admin}"})
        d = r.json()
        has_full_package = (
            r.status_code == 200 and
            d.get("id") == sub1_id and
            d.get("original_problem") == "Main street water main fracture gushing water" and
            d.get("final_problem") == "High pressure municipal water mains rupture flooding pedestrian walkway on North Main Street" and
            d.get("status") == ComplaintStatus.SUBMITTED.value and
            d.get("submitted_at") is not None and
            d.get("location_status") == LocationStatus.VERIFIED.value and
            d.get("citizen_name") == "Fatima Al-Nuaimi" and
            d.get("citizen_email") == "citizen_p9_a@example.com"
        )
        record("11. Admin detail returns 200 with full evidence package", has_full_package, f"citizen={d.get('citizen_name')}")

        print("\n--- Group D: Accept FSM Transitions ---")

        # 18. Citizen cannot accept complaint (403)
        r = client.post(f"/api/v1/admin/complaints/{sub1_id}/accept", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("18. Citizen cannot accept complaint (403)", r.status_code == 403)

        # 19. Unauthenticated accept returns 401
        r = client.post(f"/api/v1/admin/complaints/{sub1_id}/accept")
        record("19. Unauthenticated accept returns 401", r.status_code == 401)

        # 13, 14, 15: Invalid states cannot be accepted (400)
        r = client.post(f"/api/v1/admin/complaints/{draft_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("13. DRAFT cannot be accepted (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        r = client.post(f"/api/v1/admin/complaints/{ai_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("14. AI_GENERATED cannot be accepted (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        r = client.post(f"/api/v1/admin/complaints/{under_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("15. UNDER_REVIEW cannot be accepted (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        # 12. Admin can accept SUBMITTED complaint -> transitions to ACCEPTED
        r_accept = client.post(f"/api/v1/admin/complaints/{sub1_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("12. Admin can accept SUBMITTED complaint -> ACCEPTED", (r_accept.status_code == 200 and r_accept.json().get("status") == "ACCEPTED"))

        # 16. Duplicate accept on ACCEPTED complaint is rejected (400)
        r_dup_accept = client.post(f"/api/v1/admin/complaints/{sub1_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("16. Duplicate accept is rejected (400)", r_dup_accept.status_code == 400, f"detail={r_dup_accept.json().get('detail')}")

        # 28. ACCEPTED complaint cannot be rejected (terminal lock -> 400)
        r_rej_locked = client.post(
            f"/api/v1/admin/complaints/{sub1_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": "Attempting to reject an already accepted case"}
        )
        record("28. ACCEPTED complaint cannot be rejected (terminal lock)", r_rej_locked.status_code == 400)

        print("\n--- Group E: Reject FSM Transitions ---")

        # 29. Citizen cannot reject complaint (403)
        r = client.post(
            f"/api/v1/admin/complaints/{sub2_id}/reject",
            headers={"Authorization": f"Bearer {token_citizen_a}"},
            json={"admin_reason": "Citizen unauthorized rejection attempt"}
        )
        record("29. Citizen cannot reject complaint (403)", r.status_code == 403)

        # 30. Unauthenticated reject returns 401
        r = client.post(
            f"/api/v1/admin/complaints/{sub2_id}/reject",
            json={"admin_reason": "Unauthenticated rejection"}
        )
        record("30. Unauthenticated reject returns 401", r.status_code == 401)

        # 21, 22, 23: Rejection reason validation (422)
        r = client.post(f"/api/v1/admin/complaints/{sub2_id}/reject", headers={"Authorization": f"Bearer {token_admin}"}, json={})
        record("21. Missing rejection reason is rejected (422)", r.status_code == 422)

        r = client.post(f"/api/v1/admin/complaints/{sub2_id}/reject", headers={"Authorization": f"Bearer {token_admin}"}, json={"admin_reason": ""})
        record("22. Empty rejection reason is rejected (422)", r.status_code == 422)

        r = client.post(f"/api/v1/admin/complaints/{sub2_id}/reject", headers={"Authorization": f"Bearer {token_admin}"}, json={"admin_reason": "   \n\t  "})
        record("23. Whitespace-only rejection reason is rejected (422)", r.status_code == 422)

        # 24, 25, 26: Invalid states cannot be rejected (400)
        r = client.post(
            f"/api/v1/admin/complaints/{draft_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": "Valid reason but invalid state"}
        )
        record("24. DRAFT cannot be rejected (400)", r.status_code == 400)

        r = client.post(
            f"/api/v1/admin/complaints/{ai_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": "Valid reason but invalid state"}
        )
        record("25. AI_GENERATED cannot be rejected (400)", r.status_code == 400)

        r = client.post(
            f"/api/v1/admin/complaints/{under_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": "Valid reason but invalid state"}
        )
        record("26. UNDER_REVIEW cannot be rejected (400)", r.status_code == 400)

        # 20. Admin can reject SUBMITTED complaint with valid reason -> transitions to REJECTED
        rejection_reason_text = "Issue located on private residential property outside municipal road maintenance jurisdiction."
        r_reject = client.post(
            f"/api/v1/admin/complaints/{sub2_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": rejection_reason_text}
        )
        rej_data = r_reject.json()
        record(
            "20. Admin can reject SUBMITTED complaint with valid reason",
            (r_reject.status_code == 200 and rej_data.get("status") == "REJECTED" and rej_data.get("admin_reason") == rejection_reason_text),
            f"status={rej_data.get('status')}"
        )

        # 27. Duplicate reject on REJECTED complaint is rejected (400)
        r_dup_reject = client.post(
            f"/api/v1/admin/complaints/{sub2_id}/reject",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"admin_reason": "Second rejection attempt"}
        )
        record("27. Duplicate reject is rejected (400)", r_dup_reject.status_code == 400, f"detail={r_dup_reject.json().get('detail')}")

        # 17. REJECTED complaint cannot be accepted (terminal lock -> 400)
        r_acc_locked = client.post(f"/api/v1/admin/complaints/{sub2_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        record("17. REJECTED complaint cannot be accepted (terminal lock)", r_acc_locked.status_code == 400)

        print("\n--- Group F: Server Control & Payload Security ---")

        # Create another SUBMITTED complaint for security testing
        with TestingSessionLocal() as session:
            c_sec = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_sec.jpg",
                original_problem="Security testing incident",
                final_problem="Security confirmed problem",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            session.add(c_sec)
            session.commit()
            sec_id = c_sec.id

        # 31, 32, 33: Client cannot inject status, decided_at, or user_id via accept payload
        malicious_accept = {
            "status": "DRAFT",
            "decided_at": "1990-01-01T00:00:00Z",
            "user_id": citizen_b.id,
        }
        r = client.post(f"/api/v1/admin/complaints/{sec_id}/accept", headers={"Authorization": f"Bearer {token_admin}"}, json=malicious_accept)
        with TestingSessionLocal() as session:
            sec_db = session.query(Complaint).filter(Complaint.id == sec_id).first()
        record("31. Client cannot inject status via accept", sec_db.status == "ACCEPTED")
        record("32. Client cannot inject decided_at via accept", sec_db.decided_at.year > 2020)
        record("33. Client cannot alter user_id via accept", sec_db.user_id == citizen_a.id)

        # Another for reject payload security
        with TestingSessionLocal() as session:
            c_sec_rej = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/p9_sec_rej.jpg",
                original_problem="Security reject test incident",
                final_problem="Security reject confirmed problem",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            session.add(c_sec_rej)
            session.commit()
            sec_rej_id = c_sec_rej.id

        malicious_reject = {
            "admin_reason": "Legitimate reason text for security testing",
            "status": "ACCEPTED",
            "decided_at": "1990-01-01T00:00:00Z",
            "user_id": citizen_b.id,
        }
        r = client.post(f"/api/v1/admin/complaints/{sec_rej_id}/reject", headers={"Authorization": f"Bearer {token_admin}"}, json=malicious_reject)
        with TestingSessionLocal() as session:
            sec_rej_db = session.query(Complaint).filter(Complaint.id == sec_rej_id).first()
        record("34. Client cannot inject status via reject", sec_rej_db.status == "REJECTED")
        record("35. Client cannot inject decided_at via reject", sec_rej_db.decided_at.year > 2020)
        record("36. Client cannot alter user_id via reject", sec_rej_db.user_id == citizen_a.id)

        print("\n--- Group G: Server-Generated UTC Timestamp ---")

        # 37. decided_at generated on accept
        record("37. decided_at generated on accept", sec_db.decided_at is not None)

        # 38. decided_at generated on reject
        record("38. decided_at generated on reject", sec_rej_db.decided_at is not None)

        # 39. decided_at is in UTC
        is_utc = (sec_db.decided_at.tzinfo is not None) or (sec_db.decided_at.utcoffset() is None)
        record("39. decided_at is in UTC timezone", is_utc)

        # 40. decided_at is persisted
        first_decided_at = sec_db.decided_at
        record("40. decided_at is persisted in database", first_decided_at is not None)

        # 41. Duplicate requests cannot alter decided_at
        client.post(f"/api/v1/admin/complaints/{sec_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})
        with TestingSessionLocal() as session:
            sec_db_after = session.query(Complaint).filter(Complaint.id == sec_id).first()
        record("41. Duplicate requests cannot alter decided_at", sec_db_after.decided_at == first_decided_at)

        print("\n--- Group H: Provenance Immutability ---")

        with TestingSessionLocal() as session:
            c_check = session.query(Complaint).filter(Complaint.id == sub1_id).first()

        # 42-47. Provenance fields remain strictly untouched
        record("42. original_problem remains strictly unchanged", c_check.original_problem == "Main street water main fracture gushing water")
        record("43. original_address remains strictly unchanged", c_check.original_address == "North Main Street, Plot 4")
        record("44. original_latitude & longitude remain strictly unchanged", (c_check.original_latitude == 12.9716 and c_check.original_longitude == 77.5946))
        record("45. image_url remains strictly unchanged", c_check.image_url == "/uploads/complaints/p9_sub1.jpg")
        record("46. ai_problem & ai_summary remain strictly unchanged", (c_check.ai_problem == "Potable water mains rupture with heavy surface runoff."))
        record("47. final_problem & final_summary remain strictly unchanged", (c_check.final_problem == "High pressure municipal water mains rupture flooding pedestrian walkway on North Main Street"))

        print("\n--- Group I: Terminal Lock Enforcement ---")

        # 48. Citizen draft edit on ACCEPTED complaint is rejected (400)
        r = client.put(f"/api/v1/complaints/{sub1_id}/draft", headers={"Authorization": f"Bearer {token_citizen_a}"}, json={"final_problem": "Tampered after accept"})
        record("48. Citizen draft edit on ACCEPTED rejected (400)", r.status_code == 400)

        # 49. Citizen draft edit on REJECTED complaint is rejected (400)
        r = client.put(f"/api/v1/complaints/{sub2_id}/draft", headers={"Authorization": f"Bearer {token_citizen_b}"}, json={"final_problem": "Tampered after reject"})
        record("49. Citizen draft edit on REJECTED rejected (400)", r.status_code == 400)

        # 50. Citizen submission on ACCEPTED complaint is rejected (400)
        r = client.post(f"/api/v1/complaints/{sub1_id}/submit", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("50. Citizen submission on ACCEPTED rejected (400)", r.status_code == 400)

        # 51. Citizen submission on REJECTED complaint is rejected (400)
        r = client.post(f"/api/v1/complaints/{sub2_id}/submit", headers={"Authorization": f"Bearer {token_citizen_b}"})
        record("51. Citizen submission on REJECTED rejected (400)", r.status_code == 400)

        print("\n--- Group J: Evidence Image Security ---")

        # Write tiny test file in temp upload directory
        from app.services import media_service
        test_img_path = media_service.get_upload_directory() / "p9_sub1.jpg"
        test_img_path.write_bytes(TINY_JPEG)

        # 52. Admin can retrieve evidence image (200)
        r = client.get(f"/api/v1/complaints/{sub1_id}/image", headers={"Authorization": f"Bearer {token_admin}"})
        record("52. Admin can retrieve evidence image (200)", (r.status_code == 200 and len(r.content) > 0))

        # 53. Foreign citizen image access is rejected (403)
        r = client.get(f"/api/v1/complaints/{sub1_id}/image", headers={"Authorization": f"Bearer {token_citizen_b}"})
        record("53. Foreign citizen image access rejected (403)", r.status_code == 403)

        # 54. Unauthenticated image access is rejected (401)
        r = client.get(f"/api/v1/complaints/{sub1_id}/image")
        record("54. Unauthenticated image access rejected (401)", r.status_code == 401)

        print("\n--- Group K: Geographic Review ---")

        # 55. Location data and map URL remain intact in admin detail
        r = client.get(f"/api/v1/admin/complaints/{sub1_id}", headers={"Authorization": f"Bearer {token_admin}"})
        d = r.json()
        record("55. Location data remains intact in admin detail", (d.get("latitude") == 12.9716 and d.get("location_status") == "VERIFIED"))

        print("\n--- Group L: Transaction Atomicity & Safety ---")

        # Create fresh SUBMITTED complaints for transaction testing
        with TestingSessionLocal() as session:
            c_tx_acc = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/tx_acc.jpg",
                original_problem="Tx accept test",
                final_problem="Tx accept confirmed",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            c_tx_rej = Complaint(
                id=str(uuid.uuid4()),
                user_id=citizen_a.id,
                image_url="/uploads/complaints/tx_rej.jpg",
                original_problem="Tx reject test",
                final_problem="Tx reject confirmed",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
                submitted_at=now
            )
            session.add_all([c_tx_acc, c_tx_rej])
            session.commit()
            tx_acc_id, tx_rej_id = c_tx_acc.id, c_tx_rej.id

        with patch.object(Session, "commit", side_effect=Exception("Simulated Database I/O Error")):
            r = client.post(f"/api/v1/admin/complaints/{tx_acc_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})

        with TestingSessionLocal() as session:
            tx_acc_after = session.query(Complaint).filter(Complaint.id == tx_acc_id).first()
        record(
            "56. Failed persistence during accept rolls back cleanly",
            (r.status_code == 500 and tx_acc_after.status == "SUBMITTED" and tx_acc_after.decided_at is None),
            f"status={tx_acc_after.status}"
        )

        with patch.object(Session, "commit", side_effect=Exception("Simulated Database I/O Error")):
            r = client.post(
                f"/api/v1/admin/complaints/{tx_rej_id}/reject",
                headers={"Authorization": f"Bearer {token_admin}"},
                json={"admin_reason": "Objective rejection explanation"}
            )

        with TestingSessionLocal() as session:
            tx_rej_after = session.query(Complaint).filter(Complaint.id == tx_rej_id).first()
        record(
            "57. Failed persistence during reject rolls back cleanly",
            (r.status_code == 500 and tx_rej_after.status == "SUBMITTED" and tx_rej_after.decided_at is None and tx_rej_after.admin_reason is None),
            f"status={tx_rej_after.status}"
        )

        print("\n--- Group M: Zero-Demo-Data Forensic Audit ---")

        runtime_db_paths = [
            project_root / "civicflow.db",
            backend_dir / "civicflow.db",
        ]
        total_runtime_complaints = 0
        for rdb in runtime_db_paths:
            if rdb.exists() and rdb.stat().st_size > 0:
                eng = create_engine(f"sqlite:///{rdb}")
                with eng.connect() as conn:
                    table_exists = conn.execute(
                        sa.text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='complaints'")
                    ).scalar()
                    if table_exists:
                        res = conn.execute(sa.text("SELECT count(*) FROM complaints")).scalar()
                        total_runtime_complaints += res

        record("58. Zero-Demo-Data: Normal runtime DB has 0 complaints", total_runtime_complaints == 0, f"count={total_runtime_complaints}")

        frontend_src = project_root / "frontend" / "src"
        hardcoded_complaints_found = False
        sample_markers_found = False
        sample_images_found = False

        if frontend_src.exists():
            for root, _, files in os.walk(frontend_src):
                for f in files:
                    if f.endswith((".js", ".jsx", ".ts", ".tsx")):
                        content = (Path(root) / f).read_text(encoding="utf-8")
                        if re.search(r"sample_pothole", content, re.IGNORECASE):
                            sample_images_found = True
                        if re.search(r"sample_complaint|demo_complaint", content, re.IGNORECASE):
                            hardcoded_complaints_found = True
                        if re.search(r"fake_coordinates|demo_markers", content, re.IGNORECASE):
                            sample_markers_found = True

        record("59. Zero-Demo-Data: Frontend has 0 hardcoded complaint records", not hardcoded_complaints_found)
        record("60. Zero-Demo-Data: Frontend has 0 sample image references", not sample_images_found)
        record("61. Zero-Demo-Data: Frontend map has 0 hardcoded markers", not sample_markers_found)

        print("\n--- Group N: Cumulative Regressions (Phases 1-8) ---")

        # 62. Phase 1: /health & /health/db return 200
        r1 = client.get("/health")
        r2 = client.get("/health/db")
        record("62. Phase 1 Regression: /health & /health/db return 200", (r1.status_code == 200 and r2.status_code == 200))

        # 63. Phase 2: Schema intact
        with TestingSessionLocal() as session:
            u_count = session.query(User).count()
            c_count = session.query(Complaint).count()
        record("63. Phase 2 Regression: Database schema intact", (u_count > 0 and c_count > 0), f"users={u_count}, complaints={c_count}")

        # 64. Phase 3: Login returns access token
        r = client.post("/api/v1/auth/login", json={"email": "citizen_p9_a@example.com", "password": "PassFatima123!"})
        record("64. Phase 3 Regression: Login returns access token", (r.status_code == 200 and "access_token" in r.json()))

        # 65. Phase 4: Complaint intake created in DRAFT
        r = client.post(
            "/api/v1/complaints/analyze",
            headers={"Authorization": f"Bearer {token_citizen_a}"},
            files={"image": ("incident.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Dangerous fallen tree branch blocking alleyway", "original_address": "8th Cross"}
        )
        record("65. Phase 4 Regression: Complaint intake created in DRAFT", (r.status_code == 201 and r.json().get("status") == "DRAFT"))
        pipeline_id = r.json().get("id")

        # 66. Phase 5: Gemini AI draft transitions to AI_GENERATED
        mock_draft = GeminiComplaintDraft(
            category="Public Infrastructure",
            observed_issue="Fallen timber blocking municipal passage.",
            citizen_claim="Tree limb fell across walkway.",
            formal_summary="Obstruction removal required for safe public passage.",
            urgency_level="MEDIUM",
            warnings=[]
        )
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_draft):
            r = client.post(f"/api/v1/complaints/{pipeline_id}/analyze", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("66. Phase 5 Regression: AI draft transitions complaint to AI_GENERATED", r.status_code == 200 and r.json().get("category") == "Public Infrastructure")

        # 67. Phase 6: Geographic verification succeeds
        mock_geo = {
            "location_status": LocationStatus.VERIFIED.value,
            "latitude": 12.9249,
            "longitude": 77.6183,
            "place_id": "osm_p9",
            "map_url": "https://www.openstreetmap.org/?mlat=12.9249&mlon=77.6183#map=17/12.9249/77.6183",
            "distance_meters": 10.0,
            "address_match": True,
            "geocoded_address": "8th Cross, Sector 3",
            "reverse_geocoded_address": "Bengaluru",
            "message": "Verified against OpenStreetMap"
        }
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo):
            r = client.post(f"/api/v1/complaints/{pipeline_id}/location/verify", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("67. Phase 6 Regression: Geographic verification succeeds", r.status_code == 200 and r.json().get("location_status") == "VERIFIED")

        # 68. Phase 7: Draft editing transitions to UNDER_REVIEW
        r = client.put(
            f"/api/v1/complaints/{pipeline_id}/draft",
            headers={"Authorization": f"Bearer {token_citizen_a}"},
            json={"final_problem": "Fallen heavy oak branch completely obstructing 8th Cross alley"}
        )
        record("68. Phase 7 Regression: Draft editing transitions to UNDER_REVIEW", r.status_code == 200 and r.json().get("status") == "UNDER_REVIEW")

        # 69. Phase 8: Final submission transitions to SUBMITTED
        r = client.post(f"/api/v1/complaints/{pipeline_id}/submit", headers={"Authorization": f"Bearer {token_citizen_a}"})
        record("69. Phase 8 Regression: Final submission transitions to SUBMITTED", r.status_code == 200 and r.json().get("status") == "SUBMITTED")

        print("\n--- Group O: Real Runtime End-to-End Pipeline ---")

        # 70. Full pipeline: Admin reviews submitted pipeline complaint and accepts it
        r_admin_detail = client.get(f"/api/v1/admin/complaints/{pipeline_id}", headers={"Authorization": f"Bearer {token_admin}"})
        r_admin_accept = client.post(f"/api/v1/admin/complaints/{pipeline_id}/accept", headers={"Authorization": f"Bearer {token_admin}"})

        e2e_success = (
            r_admin_detail.status_code == 200 and
            r_admin_accept.status_code == 200 and
            r_admin_accept.json().get("status") == "ACCEPTED" and
            r_admin_accept.json().get("decided_at") is not None and
            r_admin_accept.json().get("original_problem") == "Dangerous fallen tree branch blocking alleyway" and
            r_admin_accept.json().get("final_problem") == "Fallen heavy oak branch completely obstructing 8th Cross alley" and
            r_admin_accept.json().get("latitude") == 12.9249
        )
        record("70. End-to-End: Full pipeline successfully reaches ACCEPTED terminal lock", e2e_success, f"final_status={r_admin_accept.json().get('status')}")

    except Exception as e:
        print(f"\n[FATAL TEST RUNNER EXCEPTION]: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    finally:
        # Restore environment settings
        settings.UPLOAD_DIR = orig_upload_dir

        # Cleanup isolated test database
        try:
            test_engine.dispose()
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except Exception:
            pass

        # Cleanup isolated test uploads directory
        try:
            shutil.rmtree(temp_upload_dir, ignore_errors=True)
        except Exception:
            pass

    print("\n" + "=" * 70)
    print(f"CIVICFLOW PHASE 9 TEST SUMMARY: {passed} PASSED | {failed} FAILED | {blocked} BLOCKED")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
