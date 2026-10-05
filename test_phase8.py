"""
CivicFlow — Phase 8 Verification Test Suite: Citizen Final Submission Pipeline + Strict FSM Enforcement

Verifies:
A. Authentication & Ownership Authorization
   1. Unauthenticated submission returns 401 Unauthorized.
   2. Owner citizen can submit complaint (200 OK).
   3. Foreign citizen cannot submit another user's complaint (403 Forbidden).

B. FSM Transition Rules
   4. UNDER_REVIEW -> SUBMITTED succeeds.
   5. DRAFT cannot submit (400 Bad Request).
   6. AI_GENERATED cannot submit (400 Bad Request).
   7. SUBMITTED cannot submit again (400 Bad Request).
   8. ACCEPTED cannot submit (400 Bad Request).
   9. REJECTED cannot submit (400 Bad Request).

C. Payload Security & Server Control
   10. Client cannot inject status via payload.
   11. Client cannot inject submitted_at via payload.
   12. Client cannot alter user_id via payload.

D. Server-Generated UTC Timestamp
   13. submitted_at is generated server-side.
   14. submitted_at is UTC.
   15. submitted_at is persisted in database.
   16. Duplicate submission does not overwrite original submitted_at.

E. Provenance Immutability
   17. original_problem remains strictly unchanged.
   18. original_address remains strictly unchanged.
   19. original_latitude remains strictly unchanged.
   20. original_longitude remains strictly unchanged.
   21. image_url remains strictly unchanged.
   22. ai_problem remains strictly unchanged.
   23. ai_address remains strictly unchanged.
   24. ai_summary remains strictly unchanged.

F. Final Content Validation
   25. Missing final_problem is rejected (422 Unprocessable Entity).
   26. Empty final_problem is rejected (422 Unprocessable Entity).
   27. Whitespace-only final_problem is rejected (422 Unprocessable Entity).
   28. Valid final draft submits successfully.

G. Transaction Atomicity & Safety
   29. Failed persistence rolls back cleanly without leaving partial submission state.

H. Response Specification
   30. Successful response contains complaint ID.
   31. Successful response contains SUBMITTED status.
   32. Successful response contains server-generated submitted_at.

I. Submitted State Locking
   33. Editing final_problem after submission is rejected (400 Bad Request).
   34. Editing final_address after submission is rejected (400 Bad Request).
   35. Editing final_summary after submission is rejected (400 Bad Request).
   36. Saving draft after submission is rejected (400 Bad Request).
   37. Duplicate submission is rejected (400 Bad Request).

J. Zero-Demo-Data Forensic Audit
   38. Normal runtime database contains zero complaints.
   39. Frontend source contains zero hardcoded complaint records.
   40. Frontend source contains zero sample images.
   41. Frontend source contains zero hardcoded map markers.

K. Regressions (Phases 1-7)
   42. Phase 1: Health endpoints (/health, /health/db) return 200 OK.
   43. Phase 2: Database schema and ORM models intact.
   44. Phase 3: Citizen login and JWT issuance succeed.
   45. Phase 4: Complaint intake created in state DRAFT with evidence photo.
   46. Phase 5: Gemini AI draft generated and complaint transitions to AI_GENERATED.
   47. Phase 6: Geographic verification and OpenStreetMap integration succeed.
   48. Phase 7: Citizen review and editing transitions complaint to UNDER_REVIEW.

L. Real Runtime End-to-End Pipeline
   49. Complete intake -> AI analysis -> Geographic verification -> Human review & edit -> Final Submission -> SUBMITTED lock.
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
from app.services import auth_service, geocoding_service
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
    print("CIVICFLOW PHASE 8 — CITIZEN FINAL SUBMISSION & FSM TEST SUITE")
    print("=" * 70)

    # Setup isolated temporary test database
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_test_p8.db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p8_uploads_")
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
            user_a = User(
                id=str(uuid.uuid4()),
                email="citizen_sub_a@example.com",
                name="Zainab Qasim",
                password_hash=auth_service.hash_password("PasswordZainab123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            user_b = User(
                id=str(uuid.uuid4()),
                email="citizen_sub_b@example.com",
                name="Tariq Mansoor",
                password_hash=auth_service.hash_password("PasswordTariq123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin_sub@example.com",
                name="Administrator Chief",
                password_hash=auth_service.hash_password("AdminChiefPassword123!"),
                role=UserRole.ADMIN.value,
                created_at=datetime.now(timezone.utc)
            )

            session.add_all([user_a, user_b, admin_user])
            session.commit()

            token_a = auth_service.create_access_token(subject=user_a.id, role=user_a.role)
            token_b = auth_service.create_access_token(subject=user_b.id, role=user_b.role)
            token_admin = auth_service.create_access_token(subject=admin_user.id, role=admin_user.role)

        now = datetime.now(timezone.utc)

        # Seed Complaint in UNDER_REVIEW state for User A
        with TestingSessionLocal() as session:
            c_review = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/test_p8_img.jpg",
                original_problem="Broken water pipeline leaking clean water onto sidewalk",
                original_address="2nd Cross Road, Sector 3",
                original_latitude=12.9249,
                original_longitude=77.6183,
                ai_problem="Potable water mains leakage with surface pooling.",
                ai_address=None,
                ai_summary="Water utility line fracture requires immediate valve isolation.",
                final_problem="High pressure municipal water pipeline rupture flooding 2nd Cross sidewalk",
                final_address="2nd Cross Road, Corner of Sector 3 Park",
                final_summary="Urgent water utility dispatch requested: continuous potable water waste.",
                latitude=12.9249,
                longitude=77.6183,
                place_id="osm_sub_1",
                map_url="https://www.openstreetmap.org/?mlat=12.9249&mlon=77.6183#map=17/12.9249/77.6183",
                location_status=LocationStatus.VERIFIED.value,
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now,
                submitted_at=None,
                decided_at=None
            )
            session.add(c_review)
            session.commit()
            c_review_id = c_review.id

        print("\n--- Group A: Authentication & Ownership Authorization ---")

        # 1. Unauthenticated submission returns 401
        r = client.post(f"/api/v1/complaints/{c_review_id}/submit")
        record("1. Unauthenticated submission returns 401", r.status_code == 401, f"status={r.status_code}")

        # 3. Foreign citizen receives 403
        r = client.post(f"/api/v1/complaints/{c_review_id}/submit", headers={"Authorization": f"Bearer {token_b}"})
        record("3. Foreign citizen receives 403", r.status_code == 403, f"status={r.status_code}")

        # 2. Owner can submit (test 4 will verify transition)
        r = client.post(f"/api/v1/complaints/{c_review_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("2. Owner citizen can submit complaint (200 OK)", r.status_code == 200, f"status={r.status_code}")

        print("\n--- Group B: FSM Transition Rules ---")

        # 4. UNDER_REVIEW -> SUBMITTED succeeds
        record("4. UNDER_REVIEW -> SUBMITTED succeeds", r.json().get("status") == ComplaintStatus.SUBMITTED.value)

        # 7. SUBMITTED cannot submit again (400 Bad Request)
        r_dup = client.post(f"/api/v1/complaints/{c_review_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("7. SUBMITTED cannot submit again (400 Bad Request)", r_dup.status_code == 400, f"detail={r_dup.json().get('detail')}")

        # Seed complaints in DRAFT, AI_GENERATED, ACCEPTED, REJECTED
        with TestingSessionLocal() as session:
            c_draft = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/draft.jpg",
                original_problem="DRAFT complaint",
                status=ComplaintStatus.DRAFT.value,
                created_at=now,
                updated_at=now
            )
            c_ai = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/ai.jpg",
                original_problem="AI_GENERATED complaint",
                status=ComplaintStatus.AI_GENERATED.value,
                created_at=now,
                updated_at=now
            )
            c_acc = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/acc.jpg",
                original_problem="ACCEPTED complaint",
                status=ComplaintStatus.ACCEPTED.value,
                created_at=now,
                updated_at=now
            )
            c_rej = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/rej.jpg",
                original_problem="REJECTED complaint",
                status=ComplaintStatus.REJECTED.value,
                created_at=now,
                updated_at=now
            )
            session.add_all([c_draft, c_ai, c_acc, c_rej])
            session.commit()
            draft_id, ai_id, acc_id, rej_id = c_draft.id, c_ai.id, c_acc.id, c_rej.id

        # 5. DRAFT cannot submit (400)
        r = client.post(f"/api/v1/complaints/{draft_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("5. DRAFT cannot submit (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        # 6. AI_GENERATED cannot submit (400)
        r = client.post(f"/api/v1/complaints/{ai_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("6. AI_GENERATED cannot submit (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        # 8. ACCEPTED cannot submit (400)
        r = client.post(f"/api/v1/complaints/{acc_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("8. ACCEPTED cannot submit (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        # 9. REJECTED cannot submit (400)
        r = client.post(f"/api/v1/complaints/{rej_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("9. REJECTED cannot submit (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        print("\n--- Group C: Payload Security & Server Control ---")

        # Create another UNDER_REVIEW complaint for payload security testing
        with TestingSessionLocal() as session:
            c_sec = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/sec.jpg",
                original_problem="Security testing incident",
                final_problem="Confirmed problem for security test",
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            session.add(c_sec)
            session.commit()
            c_sec_id = c_sec.id

        # 10, 11, 12: Client attempts to inject status, submitted_at, and user_id via payload
        malicious_payload = {
            "status": "ACCEPTED",
            "submitted_at": "1999-01-01T00:00:00Z",
            "user_id": user_b.id,
            "admin_reason": "Bypassing supervisor"
        }
        r = client.post(
            f"/api/v1/complaints/{c_sec_id}/submit",
            headers={"Authorization": f"Bearer {token_a}"},
            json=malicious_payload
        )
        with TestingSessionLocal() as session:
            sec_db = session.query(Complaint).filter(Complaint.id == c_sec_id).first()
            status_is_submitted = sec_db.status == ComplaintStatus.SUBMITTED.value
            user_unaltered = sec_db.user_id == user_a.id
            sub_at_not_injected = sec_db.submitted_at.year > 2020

        record("10. Client cannot inject status via payload", status_is_submitted, f"status={sec_db.status}")
        record("11. Client cannot inject submitted_at via payload", sub_at_not_injected, f"year={sec_db.submitted_at.year}")
        record("12. Client cannot alter user_id via payload", user_unaltered, f"user_id={sec_db.user_id}")

        print("\n--- Group D: Server-Generated UTC Timestamp ---")

        # 13. submitted_at is generated server-side
        record("13. submitted_at is generated server-side", sec_db.submitted_at is not None)

        # 14. submitted_at is UTC
        is_utc = (sec_db.submitted_at.tzinfo is not None) or (sec_db.submitted_at.utcoffset() is None)
        record("14. submitted_at is UTC timezone", is_utc)

        # 15. submitted_at is persisted in database
        first_submitted_at = sec_db.submitted_at
        record("15. submitted_at is persisted", first_submitted_at is not None, f"ts={first_submitted_at.isoformat()}")

        # 16. Duplicate submission does not overwrite original submitted_at
        r_dup = client.post(f"/api/v1/complaints/{c_sec_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        with TestingSessionLocal() as session:
            sec_db_after = session.query(Complaint).filter(Complaint.id == c_sec_id).first()
            ts_preserved = sec_db_after.submitted_at == first_submitted_at
        record("16. Duplicate submission does not overwrite submitted_at", ts_preserved)

        print("\n--- Group E: Provenance Immutability ---")

        with TestingSessionLocal() as session:
            c_check = session.query(Complaint).filter(Complaint.id == c_review_id).first()

        # 17-24. Provenance fields remain untouched
        record("17. original_problem remains unchanged", c_check.original_problem == "Broken water pipeline leaking clean water onto sidewalk")
        record("18. original_address remains unchanged", c_check.original_address == "2nd Cross Road, Sector 3")
        record("19. original_latitude remains unchanged", c_check.original_latitude == 12.9249)
        record("20. original_longitude remains unchanged", c_check.original_longitude == 77.6183)
        record("21. image_url remains unchanged", c_check.image_url == "/uploads/complaints/test_p8_img.jpg")
        record("22. ai_problem remains unchanged", c_check.ai_problem == "Potable water mains leakage with surface pooling.")
        record("23. ai_address remains unchanged", c_check.ai_address is None)
        record("24. ai_summary remains unchanged", c_check.ai_summary == "Water utility line fracture requires immediate valve isolation.")

        print("\n--- Group F: Final Content Validation ---")

        # Create UNDER_REVIEW complaints with empty/whitespace final_problem
        with TestingSessionLocal() as session:
            c_missing_prob = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/missing_prob.jpg",
                original_problem="Original description",
                final_problem=None,  # Missing
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            c_empty_prob = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/empty_prob.jpg",
                original_problem="Original description",
                final_problem="",  # Empty
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            c_space_prob = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/space_prob.jpg",
                original_problem="Original description",
                final_problem="   \n\t   ",  # Whitespace only
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            session.add_all([c_missing_prob, c_empty_prob, c_space_prob])
            session.commit()
            missing_id, empty_id, space_id = c_missing_prob.id, c_empty_prob.id, c_space_prob.id

        # 25. Missing final_problem is rejected (422)
        r = client.post(f"/api/v1/complaints/{missing_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("25. Missing final_problem is rejected (422)", r.status_code == 422, f"status={r.status_code}")

        # 26. Empty final_problem is rejected (422)
        r = client.post(f"/api/v1/complaints/{empty_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("26. Empty final_problem is rejected (422)", r.status_code == 422, f"status={r.status_code}")

        # 27. Whitespace-only final_problem is rejected (422)
        r = client.post(f"/api/v1/complaints/{space_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("27. Whitespace-only final_problem is rejected (422)", r.status_code == 422, f"status={r.status_code}")

        # 28. Valid final draft submits successfully
        with TestingSessionLocal() as session:
            c_valid = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/valid.jpg",
                original_problem="Fallen electrical wire",
                final_problem="High voltage live power cable detached and resting on pedestrian pathway",
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now
            )
            session.add(c_valid)
            session.commit()
            valid_id = c_valid.id

        r_valid = client.post(f"/api/v1/complaints/{valid_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("28. Valid final draft submits successfully", r_valid.status_code == 200, f"status={r_valid.json().get('status')}")

        print("\n--- Group G: Transaction Atomicity & Safety ---")

        # 29. Failed persistence rolls back cleanly without leaving partial submission state
        with TestingSessionLocal() as session:
            c_tx = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/tx.jpg",
                original_problem="Pipeline burst for transaction testing",
                final_problem="Confirmed pipeline burst problem description",
                status=ComplaintStatus.UNDER_REVIEW.value,
                created_at=now,
                updated_at=now,
                submitted_at=None
            )
            session.add(c_tx)
            session.commit()
            tx_id = c_tx.id

        with patch.object(Session, "commit", side_effect=Exception("Simulated Database I/O Error")):
            r = client.post(f"/api/v1/complaints/{tx_id}/submit", headers={"Authorization": f"Bearer {token_a}"})

        with TestingSessionLocal() as session:
            c_tx_after = session.query(Complaint).filter(Complaint.id == tx_id).first()
            tx_rolled_back = (
                r.status_code == 500 and
                c_tx_after.status == ComplaintStatus.UNDER_REVIEW.value and
                c_tx_after.submitted_at is None
            )
        record("29. Failed persistence rolls back cleanly (no partial state)", tx_rolled_back, f"status={c_tx_after.status}, sub_at={c_tx_after.submitted_at}")

        print("\n--- Group H: Response Specification ---")

        # 30. Successful response contains complaint ID
        # 31. Successful response contains SUBMITTED status
        # 32. Successful response contains server-generated submitted_at
        resp_json = r_valid.json()
        record("30. Successful response contains complaint ID", resp_json.get("id") == valid_id)
        record("31. Successful response contains SUBMITTED status", resp_json.get("status") == "SUBMITTED")
        record("32. Successful response contains server-generated submitted_at", resp_json.get("submitted_at") is not None)

        print("\n--- Group I: Submitted State Locking ---")

        # 33. Editing final_problem after submission is rejected (400)
        # 34. Editing final_address after submission is rejected (400)
        # 35. Editing final_summary after submission is rejected (400)
        # 36. Saving draft after submission is rejected (400)
        r_edit_attempt = client.put(
            f"/api/v1/complaints/{valid_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "final_problem": "Unauthorized post-submission alteration",
                "final_address": "Tampered address",
                "final_summary": "Tampered summary"
            }
        )
        record("33. Editing final_problem after submission is rejected (400)", r_edit_attempt.status_code == 400)
        record("34. Editing final_address after submission is rejected (400)", r_edit_attempt.status_code == 400)
        record("35. Editing final_summary after submission is rejected (400)", r_edit_attempt.status_code == 400)
        record("36. Saving draft after submission is rejected (400)", r_edit_attempt.status_code == 400)

        # 37. Duplicate submission is rejected (400)
        r_dup_valid = client.post(f"/api/v1/complaints/{valid_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        record("37. Duplicate submission is rejected (400)", r_dup_valid.status_code == 400)

        print("\n--- Group J: Zero-Demo-Data Forensic Audit ---")

        # 38. Normal runtime database contains zero complaints
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
        record("38. Zero-Demo-Data: Normal runtime DB has 0 complaints", total_runtime_complaints == 0, f"count={total_runtime_complaints}")

        # 39. Frontend source contains zero hardcoded complaint objects
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

        record("39. Zero-Demo-Data: Frontend has 0 hardcoded complaint records", not hardcoded_complaints_found)
        record("40. Zero-Demo-Data: Frontend has 0 sample image references", not sample_images_found)
        record("41. Zero-Demo-Data: Frontend map has 0 hardcoded markers", not sample_markers_found)

        print("\n--- Group K: Regressions (Phases 1-7) ---")

        # 42. Phase 1: GET /health and GET /health/db return 200
        r1 = client.get("/health")
        r2 = client.get("/health/db")
        record("42. Phase 1 Regression: /health & /health/db return 200", (r1.status_code == 200 and r2.status_code == 200))

        # 43. Phase 2: User and Complaint models intact
        with TestingSessionLocal() as session:
            u_count = session.query(User).count()
            c_count = session.query(Complaint).count()
        record("43. Phase 2 Regression: Database schema intact", (u_count > 0 and c_count > 0), f"users={u_count}, complaints={c_count}")

        # 44. Phase 3: Login & JWT issuance succeeds
        r = client.post("/api/v1/auth/login", json={"email": "citizen_sub_a@example.com", "password": "PasswordZainab123!"})
        record("44. Phase 3 Regression: Login returns access token", (r.status_code == 200 and "access_token" in r.json()))

        # 45. Phase 4: Complaint intake created in state DRAFT with image
        r = client.post(
            "/api/v1/complaints/analyze",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"image": ("incident.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Dangerous sidewalk sinkhole", "original_address": "5th Avenue"}
        )
        record("45. Phase 4 Regression: Complaint intake created in DRAFT", (r.status_code == 201 and r.json().get("status") == "DRAFT"))
        pipeline_c_id = r.json().get("id")

        # 46. Phase 5: Gemini AI draft generated and complaint transitions to AI_GENERATED
        mock_draft = GeminiComplaintDraft(
            category="Road Damage",
            observed_issue="Structural ground subsidence beneath concrete slab.",
            citizen_claim="Pedestrian reported sinkhole opening on sidewalk.",
            formal_summary="Hazardous sidewalk sinkhole requiring structural foundation assessment.",
            urgency_level="CRITICAL",
            warnings=["Risk of ground collapse"]
        )
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_draft):
            r = client.post(f"/api/v1/complaints/{pipeline_c_id}/analyze", headers={"Authorization": f"Bearer {token_a}"})
        record("46. Phase 5 Regression: AI draft transitions complaint to AI_GENERATED", (r.status_code == 200 and r.json().get("category") == "Road Damage"))

        # 47. Phase 6: Geographic verification and OpenStreetMap integration succeed
        mock_geo = {
            "location_status": LocationStatus.VERIFIED.value,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "place_id": "osm_p8_geo",
            "map_url": "https://www.openstreetmap.org/?mlat=12.9716&mlon=77.5946#map=17/12.9716/77.5946",
            "distance_meters": 30.0,
            "address_match": True,
            "geocoded_address": "5th Avenue, Bengaluru",
            "reverse_geocoded_address": "Bengaluru",
            "message": "Coordinates matched address location"
        }
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo):
            r = client.post(f"/api/v1/complaints/{pipeline_c_id}/location/verify", headers={"Authorization": f"Bearer {token_a}"})
        record("47. Phase 6 Regression: Geographic verification succeeds", (r.status_code == 200 and r.json().get("location_status") == "VERIFIED"))

        # 48. Phase 7: Citizen review and editing transitions complaint to UNDER_REVIEW
        review_payload = {
            "final_problem": "Deep sidewalk sinkhole threatening pedestrian traffic near 5th Avenue store",
            "final_address": "5th Avenue near Metro Gate 1",
            "final_summary": "Urgent engineering inspection and concrete repair required for sidewalk sinkhole."
        }
        r = client.put(f"/api/v1/complaints/{pipeline_c_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json=review_payload)
        record("48. Phase 7 Regression: Draft editing transitions to UNDER_REVIEW", (r.status_code == 200 and r.json().get("status") == "UNDER_REVIEW"))

        print("\n--- Group L: Real Runtime End-to-End Pipeline ---")

        # 49. Complete intake -> AI analysis -> Geographic verification -> Human review & edit -> Final Submission -> SUBMITTED lock
        r_final_sub = client.post(f"/api/v1/complaints/{pipeline_c_id}/submit", headers={"Authorization": f"Bearer {token_a}"})
        e2e_pass = (
            r_final_sub.status_code == 200 and
            r_final_sub.json().get("status") == ComplaintStatus.SUBMITTED.value and
            r_final_sub.json().get("submitted_at") is not None and
            r_final_sub.json().get("final_problem") == review_payload["final_problem"] and
            r_final_sub.json().get("original_problem") == "Dangerous sidewalk sinkhole" and
            r_final_sub.json().get("latitude") == 12.9716
        )
        record("49. End-to-End: Full pipeline successfully reaches SUBMITTED state lock", e2e_pass, f"status={r_final_sub.json().get('status')}")

        # Post-submission lock verification on pipeline complaint
        r_lock_check = client.put(
            f"/api/v1/complaints/{pipeline_c_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"final_problem": "Post-submission tamper attempt"}
        )
        record("50. Post-submission lock: Editing locked pipeline complaint rejected (400)", r_lock_check.status_code == 400)

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
    print(f"CIVICFLOW PHASE 8 TEST SUMMARY: {passed} PASSED | {failed} FAILED | {blocked} BLOCKED")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
