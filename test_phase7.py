"""
CivicFlow — Phase 7 Verification Test Suite: AI Draft + Human Review UI

Verifies:
A. Authentication & Ownership Authorization
   1. Unauthenticated PUT /draft is rejected (401 Unauthorized).
   2. Unauthenticated GET /ai-draft is rejected (401 Unauthorized).
   3. Owner citizen can retrieve AI draft (200 OK).
   4. Owner citizen can edit draft and save edits (200 OK).
   5. Foreign citizen cannot retrieve another citizen's AI draft (403 Forbidden).
   6. Foreign citizen cannot edit another citizen's draft (403 Forbidden).
   7. Admin can retrieve complaint AI draft (200 OK).
   8. Admin can edit complaint draft (200 OK).
   9. Nonexistent complaint returns 404 Not Found on GET /ai-draft.
   10. Nonexistent complaint returns 404 Not Found on PUT /draft.
   11. Missing AI draft returns 404 Not Found on GET /ai-draft.

B. AI Draft Retrieval & Display Semantics
   12. Real AI draft fields (category, observed_issue, citizen_claim, formal_summary, urgency_level) are returned accurately.
   13. AI draft warnings list is preserved and returned accurately.
   14. Provenance layer: raw evidence fields remain untouched by draft retrieval.

C. Human Review & Citizen Editing
   15. final_problem can be edited and saved.
   16. final_address can be edited and saved.
   17. final_summary can be edited and saved.
   18. Empty final_problem string is rejected (422 Unprocessable Entity).
   19. Whitespace-only final_problem string is rejected (422 Unprocessable Entity).
   20. AI fields (ai_problem, ai_address, ai_summary) are strictly NOT overwritten when saving citizen edits.
   21. Original citizen problem (original_problem) remains strictly unchanged.
   22. Original citizen address (original_address) remains strictly unchanged.
   23. Original device GPS coordinates (original_latitude, original_longitude) remain strictly unchanged.
   24. Physical evidence image URL remains strictly unchanged.

D. State Machine & Transition Rules
   25. Valid transition from AI_GENERATED to UNDER_REVIEW succeeds.
   26. Valid re-save in UNDER_REVIEW stays in UNDER_REVIEW.
   27. Attempting to edit a complaint in state DRAFT is rejected (400 Bad Request).
   28. Attempting to edit a complaint in state SUBMITTED is rejected (400 Bad Request).
   29. Attempting to edit a complaint in state ACCEPTED is rejected (400 Bad Request).
   30. Attempting to edit a complaint in state REJECTED is rejected (400 Bad Request).
   31. Citizen cannot inject or manipulate status to SUBMITTED/ACCEPTED/REJECTED via payload.

E. Geographic Verification & Map Integration
   32. Existing Phase 6 location status (VERIFIED/MISMATCH/etc.) remains intact after draft update.
   33. Existing canonical latitude and longitude remain intact after draft update.
   34. Existing OpenStreetMap map_url remains intact after draft update.

F. Media & Evidence Protection
   35. Evidence image endpoint rejects unauthenticated access (401).
   36. Evidence image endpoint rejects foreign citizen access (403).
   37. Evidence image endpoint allows owner citizen access (200).

G. Zero-Demo-Data Rule Audit
   38. Normal runtime database contains zero complaints.
   39. Frontend source contains zero hardcoded complaint records.
   40. Frontend source contains zero sample images.
   41. Frontend source contains zero hardcoded map markers.

H. Regressions (Phases 1-6)
   42. Phase 1: GET /health and GET /health/db return 200.
   43. Phase 2: User and Complaint models intact.
   44. Phase 3: Login & JWT issuance succeeds.
   45. Phase 4: Complaint intake created in state DRAFT with image.
   46. Phase 5: Gemini AI draft generated and complaint transitions to AI_GENERATED.
   47. Phase 6: Geographic verification and OpenStreetMap integration succeed.

I. Real Runtime End-to-End Pipeline
   48. Complete intake -> AI analysis -> Geographic verification -> Human review & edit -> UNDER_REVIEW state lock.
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
from sqlalchemy.orm import sessionmaker
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
    print("CIVICFLOW PHASE 7 — AI DRAFT + HUMAN REVIEW UI TEST SUITE")
    print("=" * 70)

    # Setup isolated temporary test database
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_test_p7.db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p7_uploads_")
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
                email="citizen_rev_a@example.com",
                name="Fatima Noor",
                password_hash=auth_service.hash_password("PasswordFatima123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            user_b = User(
                id=str(uuid.uuid4()),
                email="citizen_rev_b@example.com",
                name="Liam Smith",
                password_hash=auth_service.hash_password("PasswordLiam123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin_rev@example.com",
                name="Supervisor Admin",
                password_hash=auth_service.hash_password("AdminSecurePassword123!"),
                role=UserRole.ADMIN.value,
                created_at=datetime.now(timezone.utc)
            )

            session.add_all([user_a, user_b, admin_user])
            session.commit()

            token_a = auth_service.create_access_token(subject=user_a.id, role=user_a.role)
            token_b = auth_service.create_access_token(subject=user_b.id, role=user_b.role)
            token_admin = auth_service.create_access_token(subject=admin_user.id, role=admin_user.role)

        print("\n--- Group A: Authentication & Ownership Authorization ---")

        # Create a complaint in AI_GENERATED state for User A
        with TestingSessionLocal() as session:
            now = datetime.now(timezone.utc)
            c1 = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/test_image1.jpg",
                original_problem="Large crater pothole on 4th cross road",
                original_address="4th Cross, Koramangala",
                original_latitude=12.9352,
                original_longitude=77.6245,
                ai_problem="Pavement cavity measuring approximately 0.5 meters in diameter.",
                ai_address=None,
                ai_summary="Hazardous roadway deterioration requiring asphalt patch.",
                final_problem=None,
                final_address=None,
                final_summary=None,
                latitude=12.9352,
                longitude=77.6245,
                place_id="osm_12345",
                map_url="https://www.openstreetmap.org/?mlat=12.9352&mlon=77.6245#map=17/12.9352/77.6245",
                location_status=LocationStatus.VERIFIED.value,
                status=ComplaintStatus.AI_GENERATED.value,
                created_at=now,
                updated_at=now,
            )
            session.add(c1)
            session.commit()
            c1_id = c1.id

            # Save structured sidecar draft for c1
            sidecar_draft = GeminiComplaintDraft(
                category="Road Damage",
                observed_issue="Pavement cavity measuring approximately 0.5 meters in diameter.",
                citizen_claim="Citizen reports severe crater pothole causing vehicular damage.",
                formal_summary="Hazardous roadway deterioration requiring asphalt patch.",
                urgency_level="HIGH",
                warnings=["Edge erosion detected", "Low lighting in surrounding area"]
            )
            gemini_agent.save_ai_draft_to_disk(c1_id, sidecar_draft)

        # 1. Unauthenticated PUT /draft rejected (401)
        r = client.put(f"/api/v1/complaints/{c1_id}/draft", json={"final_problem": "Test edit"})
        record("1. Unauthenticated PUT /draft rejected (401)", r.status_code == 401, f"status={r.status_code}")

        # 2. Unauthenticated GET /ai-draft rejected (401)
        r = client.get(f"/api/v1/complaints/{c1_id}/ai-draft")
        record("2. Unauthenticated GET /ai-draft rejected (401)", r.status_code == 401, f"status={r.status_code}")

        # 3. Owner citizen can retrieve AI draft (200 OK)
        r = client.get(f"/api/v1/complaints/{c1_id}/ai-draft", headers={"Authorization": f"Bearer {token_a}"})
        record("3. Owner citizen can retrieve AI draft (200 OK)", r.status_code == 200, f"category={r.json().get('category')}")

        # 4. Owner citizen can edit draft and save edits (200 OK)
        r = client.put(
            f"/api/v1/complaints/{c1_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "final_problem": "Severe deep pothole directly in front of house 42",
                "final_address": "4th Cross Road near House 42, Koramangala",
                "final_summary": "Urgent road repair needed for severe pothole."
            }
        )
        record("4. Owner citizen can edit draft and save edits (200 OK)", r.status_code == 200, f"new_status={r.json().get('status')}")

        # 5. Foreign citizen cannot retrieve another citizen's AI draft (403)
        r = client.get(f"/api/v1/complaints/{c1_id}/ai-draft", headers={"Authorization": f"Bearer {token_b}"})
        record("5. Foreign citizen cannot retrieve another citizen's AI draft (403)", r.status_code == 403, f"status={r.status_code}")

        # 6. Foreign citizen cannot edit another citizen's draft (403)
        r = client.put(
            f"/api/v1/complaints/{c1_id}/draft",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"final_problem": "Malicious modification"}
        )
        record("6. Foreign citizen cannot edit another citizen's draft (403)", r.status_code == 403, f"status={r.status_code}")

        # 7. Admin can retrieve complaint AI draft (200 OK)
        r = client.get(f"/api/v1/complaints/{c1_id}/ai-draft", headers={"Authorization": f"Bearer {token_admin}"})
        record("7. Admin can retrieve complaint AI draft (200 OK)", r.status_code == 200, f"status={r.status_code}")

        # 8. Admin can edit complaint draft (200 OK)
        r = client.put(
            f"/api/v1/complaints/{c1_id}/draft",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"final_problem": "Admin adjusted problem statement"}
        )
        record("8. Admin can edit complaint draft (200 OK)", r.status_code == 200, f"status={r.status_code}")

        # 9. Nonexistent complaint returns 404 on GET /ai-draft
        fake_id = str(uuid.uuid4())
        r = client.get(f"/api/v1/complaints/{fake_id}/ai-draft", headers={"Authorization": f"Bearer {token_a}"})
        record("9. Nonexistent complaint returns 404 on GET /ai-draft", r.status_code == 404, f"status={r.status_code}")

        # 10. Nonexistent complaint returns 404 on PUT /draft
        r = client.put(f"/api/v1/complaints/{fake_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": "Missing"})
        record("10. Nonexistent complaint returns 404 on PUT /draft", r.status_code == 404, f"status={r.status_code}")

        # 11. Missing AI draft returns 404 on GET /ai-draft
        with TestingSessionLocal() as session:
            raw_c = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/raw.jpg",
                original_problem="Raw intake without AI draft",
                status=ComplaintStatus.DRAFT.value,
                created_at=now,
                updated_at=now,
            )
            session.add(raw_c)
            session.commit()
            raw_c_id = raw_c.id

        r = client.get(f"/api/v1/complaints/{raw_c_id}/ai-draft", headers={"Authorization": f"Bearer {token_a}"})
        record("11. Missing AI draft returns 404 on GET /ai-draft", r.status_code == 404, f"detail={r.json().get('detail')}")

        print("\n--- Group B: AI Draft Retrieval & Display Semantics ---")

        # 12. Real AI draft fields returned accurately
        r = client.get(f"/api/v1/complaints/{c1_id}/ai-draft", headers={"Authorization": f"Bearer {token_a}"})
        draft_data = r.json()
        match_draft = (
            draft_data.get("category") == "Road Damage" and
            draft_data.get("urgency_level") == "HIGH" and
            "0.5 meters" in draft_data.get("observed_issue", "") and
            "asphalt patch" in draft_data.get("formal_summary", "")
        )
        record("12. Real AI draft fields returned accurately", match_draft, f"draft={draft_data.get('category')}")

        # 13. Warnings in AI draft returned accurately
        warnings = draft_data.get("warnings", [])
        has_warnings = len(warnings) == 2 and "Edge erosion detected" in warnings
        record("13. Warnings in AI draft returned accurately", has_warnings, f"count={len(warnings)}")

        # 14. Provenance layer: raw evidence fields remain untouched by draft retrieval
        with TestingSessionLocal() as session:
            c1_db = session.query(Complaint).filter(Complaint.id == c1_id).first()
            raw_intact = (
                c1_db.original_problem == "Large crater pothole on 4th cross road" and
                c1_db.original_address == "4th Cross, Koramangala" and
                c1_db.original_latitude == 12.9352 and
                c1_db.original_longitude == 77.6245
            )
        record("14. Provenance layer raw evidence remains untouched", raw_intact, "original_* fields intact")

        print("\n--- Group C: Human Review & Citizen Editing ---")

        # Create another complaint in AI_GENERATED state to test detailed editing
        with TestingSessionLocal() as session:
            c2 = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/test_c2.jpg",
                original_problem="Garbage dumped near transformer",
                original_address="Near Electrical Transformer, Block B",
                original_latitude=13.0827,
                original_longitude=80.2707,
                ai_problem="Solid municipal waste heap near electrical sub-unit.",
                ai_address=None,
                ai_summary="Unattended refuse presenting potential fire hazard.",
                latitude=13.0827,
                longitude=80.2707,
                place_id="osm_chennai",
                map_url="https://www.openstreetmap.org/?mlat=13.0827&mlon=80.2707#map=17/13.0827/80.2707",
                location_status=LocationStatus.VERIFIED.value,
                status=ComplaintStatus.AI_GENERATED.value,
                created_at=now,
                updated_at=now,
            )
            session.add(c2)
            session.commit()
            c2_id = c2.id

        # 15. final_problem can be edited and saved
        # 16. final_address can be edited and saved
        # 17. final_summary can be edited and saved
        edit_payload = {
            "final_problem": "Accumulated household waste directly blocking substation access gate",
            "final_address": "Block B, Substation Gate 2",
            "final_summary": "Urgent sanitation clearance requested for substation obstruction."
        }
        r = client.put(f"/api/v1/complaints/{c2_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json=edit_payload)
        resp_data = r.json()
        record("15. final_problem can be edited and saved", resp_data.get("final_problem") == edit_payload["final_problem"])
        record("16. final_address can be edited and saved", resp_data.get("final_address") == edit_payload["final_address"])
        record("17. final_summary can be edited and saved", resp_data.get("final_summary") == edit_payload["final_summary"])

        # 18. Empty final_problem string is rejected (422)
        r = client.put(f"/api/v1/complaints/{c2_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": ""})
        record("18. Empty final_problem string is rejected (422)", r.status_code == 422, f"status={r.status_code}")

        # 19. Whitespace-only final_problem string is rejected (422)
        r = client.put(f"/api/v1/complaints/{c2_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": "   \n  \t  "})
        record("19. Whitespace-only final_problem string is rejected (422)", r.status_code == 422, f"status={r.status_code}")

        # 20. AI fields are strictly NOT overwritten when saving citizen edits
        with TestingSessionLocal() as session:
            c2_refreshed = session.query(Complaint).filter(Complaint.id == c2_id).first()
            ai_untouched = (
                c2_refreshed.ai_problem == "Solid municipal waste heap near electrical sub-unit." and
                c2_refreshed.ai_summary == "Unattended refuse presenting potential fire hazard." and
                c2_refreshed.ai_address is None
            )
        record("20. AI fields are strictly NOT overwritten", ai_untouched, "ai_* preserved")

        # 21. Original citizen problem remains strictly unchanged
        record("21. original_problem remains strictly unchanged", c2_refreshed.original_problem == "Garbage dumped near transformer")

        # 22. Original citizen address remains strictly unchanged
        record("22. original_address remains strictly unchanged", c2_refreshed.original_address == "Near Electrical Transformer, Block B")

        # 23. Original device GPS remains strictly unchanged
        record("23. original_latitude & longitude remain unchanged", (c2_refreshed.original_latitude == 13.0827 and c2_refreshed.original_longitude == 80.2707))

        # 24. Physical evidence image URL remains strictly unchanged
        record("24. image_url remains strictly unchanged", c2_refreshed.image_url == "/uploads/complaints/test_c2.jpg")

        print("\n--- Group D: State Machine & Transition Rules ---")

        # 25. Valid transition from AI_GENERATED to UNDER_REVIEW succeeds
        record("25. Valid transition to UNDER_REVIEW succeeds", c2_refreshed.status == ComplaintStatus.UNDER_REVIEW.value)

        # 26. Valid re-save in UNDER_REVIEW stays in UNDER_REVIEW
        r = client.put(
            f"/api/v1/complaints/{c2_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"final_problem": "Refined problem description second revision"}
        )
        record("26. Valid re-save in UNDER_REVIEW stays in UNDER_REVIEW", r.status_code == 200 and r.json().get("status") == ComplaintStatus.UNDER_REVIEW.value)

        # 27. Attempting to edit a complaint in state DRAFT is rejected (400 Bad Request)
        r = client.put(
            f"/api/v1/complaints/{raw_c_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"final_problem": "Premature edit without AI draft"}
        )
        record("27. Edit in state DRAFT rejected (400)", r.status_code == 400, f"detail={r.json().get('detail')}")

        # 28. Attempting to edit a complaint in state SUBMITTED is rejected (400)
        with TestingSessionLocal() as session:
            sub_c = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/sub.jpg",
                original_problem="Already submitted problem",
                status=ComplaintStatus.SUBMITTED.value,
                created_at=now,
                updated_at=now,
            )
            acc_c = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/acc.jpg",
                original_problem="Accepted problem",
                status=ComplaintStatus.ACCEPTED.value,
                created_at=now,
                updated_at=now,
            )
            rej_c = Complaint(
                id=str(uuid.uuid4()),
                user_id=user_a.id,
                image_url="/uploads/complaints/rej.jpg",
                original_problem="Rejected problem",
                status=ComplaintStatus.REJECTED.value,
                created_at=now,
                updated_at=now,
            )
            session.add_all([sub_c, acc_c, rej_c])
            session.commit()
            sub_id, acc_id, rej_id = sub_c.id, acc_c.id, rej_c.id

        r = client.put(f"/api/v1/complaints/{sub_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": "Edit"})
        record("28. Edit in state SUBMITTED rejected (400)", r.status_code == 400, f"status={r.status_code}")

        # 29. Attempting to edit a complaint in state ACCEPTED is rejected (400)
        r = client.put(f"/api/v1/complaints/{acc_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": "Edit"})
        record("29. Edit in state ACCEPTED rejected (400)", r.status_code == 400, f"status={r.status_code}")

        # 30. Attempting to edit a complaint in state REJECTED is rejected (400)
        r = client.put(f"/api/v1/complaints/{rej_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json={"final_problem": "Edit"})
        record("30. Edit in state REJECTED rejected (400)", r.status_code == 400, f"status={r.status_code}")

        # 31. Citizen cannot inject or manipulate status to SUBMITTED/ACCEPTED/REJECTED via payload
        r = client.put(
            f"/api/v1/complaints/{c2_id}/draft",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "final_problem": "Attempting status injection",
                "status": "ACCEPTED",
                "admin_reason": "Bypassing admin"
            }
        )
        with TestingSessionLocal() as session:
            c2_check = session.query(Complaint).filter(Complaint.id == c2_id).first()
            status_safe = c2_check.status == ComplaintStatus.UNDER_REVIEW.value and c2_check.admin_reason is None
        record("31. Status manipulation rejected; stays UNDER_REVIEW", status_safe, f"status={c2_check.status}")

        print("\n--- Group E: Geographic Verification & Map Integration ---")

        # 32. Existing location status remains intact after draft update
        record("32. Location status remains intact (VERIFIED)", c2_check.location_status == LocationStatus.VERIFIED.value)

        # 33. Canonical coordinates remain intact
        record("33. Canonical coordinates remain intact", (c2_check.latitude == 13.0827 and c2_check.longitude == 80.2707))

        # 34. OpenStreetMap map_url remains intact
        record("34. OpenStreetMap map_url remains intact", "13.0827" in (c2_check.map_url or ""))

        print("\n--- Group F: Media & Evidence Protection ---")

        # Create real physical test image inside temp_upload_dir
        dest_img_path = Path(temp_upload_dir) / "complaints" / "test_c2.jpg"
        dest_img_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_img_path, "wb") as f:
            f.write(TINY_JPEG)

        # 35. Evidence image rejects unauthenticated access (401)
        r = client.get(f"/api/v1/complaints/{c2_id}/image")
        record("35. Evidence image rejects unauthenticated access (401)", r.status_code == 401, f"status={r.status_code}")

        # 36. Evidence image rejects foreign citizen access (403)
        r = client.get(f"/api/v1/complaints/{c2_id}/image", headers={"Authorization": f"Bearer {token_b}"})
        record("36. Evidence image rejects foreign citizen access (403)", r.status_code == 403, f"status={r.status_code}")

        # 37. Evidence image allows owner citizen access (200)
        r = client.get(f"/api/v1/complaints/{c2_id}/image", headers={"Authorization": f"Bearer {token_a}"})
        record("37. Evidence image allows owner citizen access (200)", r.status_code == 200, f"bytes={len(r.content)}")

        print("\n--- Group G: Zero-Demo-Data Rule Audit ---")

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

        print("\n--- Group H: Regressions (Phases 1-6) ---")

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
        r = client.post("/api/v1/auth/login", json={"email": "citizen_rev_a@example.com", "password": "PasswordFatima123!"})
        record("44. Phase 3 Regression: Login returns access token", (r.status_code == 200 and "access_token" in r.json()))

        # 45. Phase 4: Complaint intake created in state DRAFT with image
        r = client.post(
            "/api/v1/complaints/analyze",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"image": ("incident.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Overflowing sewer line", "original_address": "8th Main, Indiranagar"}
        )
        record("45. Phase 4 Regression: Complaint intake created in DRAFT", (r.status_code == 201 and r.json().get("status") == "DRAFT"))
        pipeline_c_id = r.json().get("id")

        # 46. Phase 5: Gemini AI draft generated and complaint transitions to AI_GENERATED
        # Mock Gemini call for fast reliable regression
        mock_draft = GeminiComplaintDraft(
            category="Drainage",
            observed_issue="Turbid wastewater escaping fractured utility conduit.",
            citizen_claim="Resident reports contaminated runoff across pedestrian sidewalk.",
            formal_summary="Defective municipal drain pipe discharging effluent onto public thoroughfare.",
            urgency_level="CRITICAL",
            warnings=["Biological hazard risk"]
        )
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_draft):
            r = client.post(f"/api/v1/complaints/{pipeline_c_id}/analyze", headers={"Authorization": f"Bearer {token_a}"})
        record("46. Phase 5 Regression: AI draft transitions complaint to AI_GENERATED", (r.status_code == 200 and r.json().get("category") == "Drainage"))

        # 47. Phase 6: Geographic verification and OpenStreetMap integration succeed
        mock_geo = {
            "location_status": LocationStatus.VERIFIED.value,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "place_id": "osm_blr_1",
            "map_url": "https://www.openstreetmap.org/?mlat=12.9716&mlon=77.5946#map=17/12.9716/77.5946",
            "distance_meters": 45.0,
            "address_match": True,
            "geocoded_address": "8th Main, Indiranagar, Bengaluru",
            "reverse_geocoded_address": "Indiranagar, Bengaluru",
            "message": "Coordinates matched address location"
        }
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo):
            r = client.post(f"/api/v1/complaints/{pipeline_c_id}/location/verify", headers={"Authorization": f"Bearer {token_a}"})
        record("47. Phase 6 Regression: Geographic verification succeeds", (r.status_code == 200 and r.json().get("location_status") == "VERIFIED"))

        print("\n--- Group I: Real Runtime End-to-End Pipeline ---")

        # 48. Complete intake -> AI analysis -> Geographic verification -> Human review & edit -> UNDER_REVIEW state lock
        # Now perform citizen human review on pipeline_c_id:
        review_edit = {
            "final_problem": "Sewage pipe overflow flooding entire pedestrian crossing at 8th Main",
            "final_address": "8th Main Road, Corner of 10th Cross, Indiranagar",
            "final_summary": "Urgent sanitary intervention required: public health risk from raw sewage overflow."
        }
        r = client.put(f"/api/v1/complaints/{pipeline_c_id}/draft", headers={"Authorization": f"Bearer {token_a}"}, json=review_edit)
        e2e_ok = (
            r.status_code == 200 and
            r.json().get("status") == ComplaintStatus.UNDER_REVIEW.value and
            r.json().get("final_problem") == review_edit["final_problem"] and
            r.json().get("final_address") == review_edit["final_address"] and
            r.json().get("final_summary") == review_edit["final_summary"] and
            r.json().get("original_problem") == "Overflowing sewer line" and
            r.json().get("latitude") == 12.9716
        )
        record("48. End-to-End: Full pipeline reaches UNDER_REVIEW state lock", e2e_ok, f"final_status={r.json().get('status')}")

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
    print(f"CIVICFLOW PHASE 7 TEST SUMMARY: {passed} PASSED | {failed} FAILED | {blocked} BLOCKED")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
