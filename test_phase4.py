"""
CivicFlow — Phase 4 Verification & Complaint Intake Test Suite

Tests all requirements for Phase 4:
A. Authentication & Intake
   1. Unauthenticated complaint creation rejected (401).
   2. Authenticated citizen can create complaint intake (201).
   3. Complaint persisted in database.
   4. UUIDv4 identifier generated.
   5. Complaint belongs to authenticated user (user_id).
   6. Initial status defaults to DRAFT.
   7. Original problem description preserved.
   8. Original address preserved.
   9. Original latitude preserved.
   10. Original longitude preserved.
   11. AI fields remain NULL (ai_problem, ai_address, ai_summary).
   12. Final fields remain NULL (final_problem, final_address, final_summary).

B. Upload Pipeline & Security
   13. Valid JPEG accepted.
   14. Valid PNG accepted.
   15. Valid WebP accepted.
   16. Missing image rejected (400).
   17. Unsupported MIME type rejected (400).
   18. Oversized image (>10MB) rejected (413).
   19. Original client filename is NOT used as storage filename.
   20. Stored file exists on disk.
   21. Stored file is located inside intended upload directory.
   22. Path traversal filename attempt safely neutralized.
   23. Fake/non-image content rejected by magic byte validator (400).

C. Ownership & RBAC Retrieval
   24. Citizen can list own complaints (GET /complaints).
   24b. List contains Citizen A's complaints and excludes Citizen B's.
   25. Citizen can retrieve own complaint (GET /complaints/{id}).
   26. Citizen cannot retrieve another citizen's complaint (403 Forbidden).
   27. Administrator can access citizen complaint (200 OK).
   28. Nonexistent complaint returns 404 Not Found.
   29. Unauthenticated retrieval returns 401 Unauthorized.
   30. Invalid coordinates rejected (e.g. lat > 90).

D. Protected Media Access & Direct Access Security
   31. Unauthenticated direct media access rejected (401).
   32. Owner direct media access succeeds (200 OK).
   33. Media response streams actual binary image bytes (content verification).
   34. Foreign citizen direct media access rejected (403 Forbidden).
   35. Administrator direct media access succeeds (200 OK).
   36. Nonexistent complaint media access returns 404 Not Found.
   37. Public static /uploads directory access is blocked (404 Not Found).

E. Phase 1, Phase 2, & Phase 3 Regressions
   38. Phase 1 Regression: GET /health returns 200 OK.
   39. Phase 1 Regression: GET /health/db returns 200 OK.
   40. Phase 2 Regression: Database schema & ORM relationships persist.
   41. Phase 3 Regression: User login and JWT authentication work.
"""

import sys
import os
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths
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

# Fix passlib / bcrypt compatibility before import
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        import types
        bcrypt.__about__ = types.SimpleNamespace(__version__=getattr(bcrypt, "__version__", "4.0.0"))
except Exception:
    pass

# Auto-check and install python-multipart if missing in current environment
try:
    import multipart
except ImportError:
    print("[*] Installing missing dependency: python-multipart...")
    import subprocess
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "python-multipart>=0.0.9"
        ])
        import multipart
    except Exception as e:
        print(f"[!] Pip install note: {e}")

import sqlalchemy as sa

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, LocationStatus
from app.config import settings
from app.services import auth_service, media_service
from app.main import app

# Minimal valid test image binaries
TINY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x02" + b"\x00" * 40 + b"\xff\xd9"
TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
TINY_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00\x02\x00\x34\x25"
FAKE_IMAGE = b"NOT_AN_IMAGE_FILE_JUST_SOME_TEXT_DATA_WITH_JPG_NAME"


def run_tests():
    print("=" * 70)
    print("CIVICFLOW PHASE 4 — CITIZEN INTAKE & MEDIA UPLOAD VERIFICATION")
    print("=" * 70)

    passed = 0
    failed = 0

    def record(name: str, condition: bool, details: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f" [PASS] {name}" + (f" -> {details}" if details else ""))
        else:
            failed += 1
            print(f" [FAIL] {name}" + (f" -> {details}" if details else ""))

    # 1. Setup Isolated Temporary SQLite Database
    temp_db_fd, temp_db_path = tempfile.mkstemp(prefix="civicflow_phase4_test_", suffix=".db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p4_uploads_")
    orig_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_upload_dir

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    created_file_paths = []

    try:
        # Pre-seed two citizens and one administrator
        with TestingSessionLocal() as session:
            citizen_a = auth_service.register_user(
                db=session,
                name="Alice Citizen",
                email="alice@example.com",
                password="PasswordAlice123!"
            )
            citizen_a_id = citizen_a.id

            citizen_b = auth_service.register_user(
                db=session,
                name="Bob Citizen",
                email="bob@example.com",
                password="PasswordBob123!"
            )
            citizen_b_id = citizen_b.id

            admin_user = auth_service.create_admin_user(
                db=session,
                name="Commissioner Gordon",
                email="gordon@cityhall.gov",
                password="AdminPassword123!"
            )
            admin_id = admin_user.id

        token_a = auth_service.create_access_token(subject=citizen_a_id, role="citizen")
        token_b = auth_service.create_access_token(subject=citizen_b_id, role="citizen")
        token_admin = auth_service.create_access_token(subject=admin_id, role="admin")

        auth_headers_a = {"Authorization": f"Bearer {token_a}"}
        auth_headers_b = {"Authorization": f"Bearer {token_b}"}
        auth_headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # =====================================================================
        # GROUP A: AUTHENTICATION & INTAKE
        # =====================================================================
        print("\n--- A. Authentication & Complaint Creation Tests ---")

        # 1. Unauthenticated complaint creation rejected (401)
        res_unauth = client.post(
            "/api/v1/complaints/analyze",
            files={"image": ("test.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Broken sidewalk"}
        )
        record("1. Unauthenticated complaint creation rejected (401)", res_unauth.status_code == 401, f"Status: {res_unauth.status_code}")

        # 2. Authenticated citizen can create complaint intake (201)
        res_create_a = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("pothole.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Deep dangerous pothole on corner of 4th St",
                "original_address": "400 Main Street, Springfield",
                "original_latitude": 39.7817,
                "original_longitude": -89.6501
            }
        )
        record("2. Authenticated citizen can create complaint intake (201)", res_create_a.status_code == 201, f"Status: {res_create_a.status_code}")
        complaint_a = res_create_a.json()
        cid_a = complaint_a.get("id")

        # 3. Complaint persisted in database
        with TestingSessionLocal() as session:
            db_complaint = session.query(Complaint).filter(Complaint.id == cid_a).first()
            persisted = db_complaint is not None
            c_uid = db_complaint.user_id if db_complaint else None
            c_status = db_complaint.status if db_complaint else None
            c_problem = db_complaint.original_problem if db_complaint else None
            c_address = db_complaint.original_address if db_complaint else None
            c_lat = db_complaint.original_latitude if db_complaint else None
            c_lng = db_complaint.original_longitude if db_complaint else None
            c_ai_p = db_complaint.ai_problem if db_complaint else "NOT_NONE"
            c_ai_a = db_complaint.ai_address if db_complaint else "NOT_NONE"
            c_ai_s = db_complaint.ai_summary if db_complaint else "NOT_NONE"
            c_fin_p = db_complaint.final_problem if db_complaint else "NOT_NONE"
            c_fin_a = db_complaint.final_address if db_complaint else "NOT_NONE"
            c_fin_s = db_complaint.final_summary if db_complaint else "NOT_NONE"
            c_image = db_complaint.image_url if db_complaint else ""

        record("3. Complaint persisted in database", persisted)

        # 4. UUIDv4 identifier generated
        record("4. UUIDv4 identifier generated", bool(cid_a) and len(cid_a) == 36 and "-" in cid_a)

        # 5. Complaint belongs to authenticated user
        record("5. Complaint belongs to authenticated user", c_uid == citizen_a_id)

        # 6. Initial status defaults to DRAFT
        record("6. Initial status defaults to DRAFT", c_status == ComplaintStatus.DRAFT.value, f"Status: {c_status}")

        # 7. Original problem preserved
        record("7. Original problem preserved", c_problem == "Deep dangerous pothole on corner of 4th St")

        # 8. Original address preserved
        record("8. Original address preserved", c_address == "400 Main Street, Springfield")

        # 9. Original latitude preserved
        record("9. Original latitude preserved", abs(c_lat - 39.7817) < 1e-4)

        # 10. Original longitude preserved
        record("10. Original longitude preserved", abs(c_lng - (-89.6501)) < 1e-4)

        # 11. AI fields remain NULL (Phase 4 Boundary)
        record("11. AI fields remain NULL", c_ai_p is None and c_ai_a is None and c_ai_s is None)

        # 12. Final fields remain NULL (Phase 4 Boundary)
        record("12. Final fields remain NULL", c_fin_p is None and c_fin_a is None and c_fin_s is None)

        # =====================================================================
        # GROUP B: UPLOAD PIPELINE & SECURITY
        # =====================================================================
        print("\n--- B. Upload Pipeline & Security Tests ---")

        # 13. Valid JPEG accepted
        res_jpeg = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("incident.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Pothole incident JPEG"}
        )
        record("13. Valid JPEG accepted", res_jpeg.status_code == 201)

        # 14. Valid PNG accepted
        res_png = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("incident.png", TINY_PNG, "image/png")},
            data={"original_problem": "Broken lamp post PNG"}
        )
        record("14. Valid PNG accepted", res_png.status_code == 201)

        # 15. Valid WebP accepted
        res_webp = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("incident.webp", TINY_WEBP, "image/webp")},
            data={"original_problem": "Overflowing dumpster WebP"}
        )
        record("15. Valid WebP accepted", res_webp.status_code == 201)

        # 16. Missing image rejected (400)
        res_no_img = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            data={"original_problem": "Complaint without photo"}
        )
        record("16. Missing image rejected (400/422)", res_no_img.status_code in [400, 422], f"Status: {res_no_img.status_code}")

        # 17. Unsupported MIME type rejected (400)
        res_bad_mime = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("script.sh", b"#!/bin/bash\necho test", "application/x-sh")},
            data={"original_problem": "Malicious script"}
        )
        record("17. Unsupported MIME type rejected (400)", res_bad_mime.status_code == 400, f"Status: {res_bad_mime.status_code}")

        # 18. Oversized image (>10MB) rejected (413)
        oversized_data = TINY_JPEG + b"0" * (11 * 1024 * 1024)  # 11 MB
        res_oversized = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("large.jpg", oversized_data, "image/jpeg")},
            data={"original_problem": "Oversized image test"}
        )
        record("18. Oversized image (>10MB) rejected (413)", res_oversized.status_code == 413, f"Status: {res_oversized.status_code}")

        # 19. Original client filename is NOT used as storage filename
        stored_url = complaint_a.get("image_url", "")
        record("19. Original client filename NOT used as storage name", "pothole.jpg" not in stored_url and stored_url.startswith("/uploads/complaints/"))

        # 20. Stored file exists on disk
        intended_upload_dir = media_service.get_upload_directory().resolve()
        filename = os.path.basename(stored_url)
        abs_stored_path = (intended_upload_dir / filename).resolve()
        file_on_disk = abs_stored_path.exists()
        created_file_paths.append(abs_stored_path)
        record("20. Stored file exists on disk", file_on_disk, f"Path: {abs_stored_path}")

        # 21. Stored file is located inside intended upload directory
        record("21. Stored file is inside intended upload directory", str(abs_stored_path).startswith(str(intended_upload_dir)))

        # 22. Path traversal attempt safely neutralized
        traversal_res = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("../../../../etc/passwd.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Path traversal filename attack"}
        )
        t_url = traversal_res.json().get("image_url", "") if traversal_res.status_code == 201 else ""
        record(
            "22. Path traversal attempt safely neutralized",
            traversal_res.status_code == 201 and ".." not in t_url and t_url.startswith("/uploads/complaints/"),
            f"Stored as: {t_url}"
        )

        # 23. Fake/non-image content rejected by magic byte validator (400)
        res_fake_img = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("malicious.jpg", FAKE_IMAGE, "image/jpeg")},
            data={"original_problem": "Disguised text file"}
        )
        record("23. Fake image rejected by binary inspection (400)", res_fake_img.status_code == 400, f"Status: {res_fake_img.status_code}")

        # =====================================================================
        # GROUP C: OWNERSHIP & RETRIEVAL
        # =====================================================================
        print("\n--- C. Ownership & RBAC Retrieval Tests ---")

        # Create a complaint belonging to Citizen B
        res_create_b = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_b,
            files={"image": ("bob_park.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Broken swing in municipal park"}
        )
        cid_b = res_create_b.json().get("id")

        # 24. Citizen can list own complaints
        res_list_a = client.get("/api/v1/complaints", headers=auth_headers_a)
        record("24. Citizen can list own complaints (200 OK)", res_list_a.status_code == 200)
        list_a_ids = [c["id"] for c in res_list_a.json()]
        record("24b. List contains Citizen A's complaints and excludes Citizen B's", cid_a in list_a_ids and cid_b not in list_a_ids)

        # 25. Citizen can retrieve own complaint
        res_get_own = client.get(f"/api/v1/complaints/{cid_a}", headers=auth_headers_a)
        record("25. Citizen can retrieve own complaint (200 OK)", res_get_own.status_code == 200 and res_get_own.json()["id"] == cid_a)

        # 26. Citizen cannot retrieve another citizen's complaint (403 Forbidden)
        res_steal = client.get(f"/api/v1/complaints/{cid_b}", headers=auth_headers_a)
        record("26. Citizen cannot retrieve another citizen's complaint (403)", res_steal.status_code == 403, f"Status: {res_steal.status_code}")

        # 27. Administrator can access citizen's complaint (200 OK)
        res_admin_access = client.get(f"/api/v1/complaints/{cid_a}", headers=auth_headers_admin)
        record("27. Administrator can access citizen's complaint (200 OK)", res_admin_access.status_code == 200 and res_admin_access.json()["id"] == cid_a)

        # 28. Nonexistent complaint returns 404 Not Found
        random_cid = str(uuid.uuid4())
        res_404 = client.get(f"/api/v1/complaints/{random_cid}", headers=auth_headers_a)
        record("28. Nonexistent complaint returns 404", res_404.status_code == 404, f"Status: {res_404.status_code}")

        # 29. Unauthenticated retrieval returns 401 Unauthorized
        res_unauth_get = client.get(f"/api/v1/complaints/{cid_a}")
        record("29. Unauthenticated retrieval returns 401", res_unauth_get.status_code == 401, f"Status: {res_unauth_get.status_code}")

        # 30. Invalid coordinates rejected (e.g. lat > 90)
        res_bad_coords = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("coords.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Invalid coords test",
                "original_latitude": 999.0,
                "original_longitude": 50.0
            }
        )
        record("30. Invalid GPS coordinates rejected (400)", res_bad_coords.status_code == 400, f"Status: {res_bad_coords.status_code}")

        # =====================================================================
        # GROUP D: PROTECTED MEDIA ACCESS & DIRECT ACCESS SECURITY
        # =====================================================================
        print("\n--- D. Protected Media Access & Direct Access Security Tests ---")

        # 31. Unauthenticated direct media access rejected (401)
        res_media_unauth = client.get(f"/api/v1/complaints/{cid_a}/image")
        record("31. Unauthenticated direct media access rejected (401)", res_media_unauth.status_code == 401, f"Status: {res_media_unauth.status_code}")

        # 32. Owner direct media access succeeds (200 OK)
        res_media_owner = client.get(f"/api/v1/complaints/{cid_a}/image", headers=auth_headers_a)
        record("32. Owner direct media access succeeds (200 OK)", res_media_owner.status_code == 200, f"Status: {res_media_owner.status_code}")

        # 33. Media response streams actual binary image bytes
        record(
            "33. Media response streams actual binary image bytes",
            res_media_owner.content == TINY_JPEG and res_media_owner.headers.get("content-type") == "image/jpeg",
            f"Bytes: {len(res_media_owner.content)}, Content-Type: {res_media_owner.headers.get('content-type')}"
        )

        # 34. Foreign citizen direct media access rejected (403 Forbidden)
        res_media_foreign = client.get(f"/api/v1/complaints/{cid_a}/image", headers=auth_headers_b)
        record("34. Foreign citizen direct media access rejected (403 Forbidden)", res_media_foreign.status_code == 403, f"Status: {res_media_foreign.status_code}")

        # 35. Administrator direct media access succeeds (200 OK)
        res_media_admin = client.get(f"/api/v1/complaints/{cid_a}/image", headers=auth_headers_admin)
        record(
            "35. Administrator direct media access succeeds (200 OK)",
            res_media_admin.status_code == 200 and res_media_admin.content == TINY_JPEG,
            f"Status: {res_media_admin.status_code}"
        )

        # 36. Nonexistent complaint media access returns 404 Not Found
        res_media_404 = client.get(f"/api/v1/complaints/{uuid.uuid4()}/image", headers=auth_headers_a)
        record("36. Nonexistent complaint media returns 404", res_media_404.status_code == 404, f"Status: {res_media_404.status_code}")

        # 37. Public static /uploads directory access is blocked (404 Not Found)
        raw_storage_url = complaint_a.get("image_url", "")
        res_static_direct = client.get(raw_storage_url)
        record(
            "37. Public static /uploads directory access is blocked (404)",
            res_static_direct.status_code == 404,
            f"Status: {res_static_direct.status_code}"
        )

        # =====================================================================
        # GROUP E: REGRESSION CHECKS (PHASES 1, 2, 3)
        # =====================================================================
        print("\n--- E. Regression Checks (Phases 1, 2, 3) ---")

        # 38. Phase 1 Health Endpoint
        r_h = client.get("/health")
        record("38. Phase 1 Regression: GET /health (200 OK)", r_h.status_code == 200 and r_h.json() == {"status": "ok"})

        # 39. Phase 1 Database Health Endpoint
        r_db = client.get("/health/db")
        record("39. Phase 1 Regression: GET /health/db (200 OK)", r_db.status_code == 200 and r_db.json().get("database", {}).get("connected") is True)

        # 40. Phase 2 Database Schema Integrity
        with TestingSessionLocal() as session:
            test_c = session.query(Complaint).first()
            record("40. Phase 2 Regression: Complaint ORM model intact", test_c is not None and hasattr(test_c, "location_status"))

        # 41. Phase 3 Authentication Login Check
        r_login = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "PasswordAlice123!"})
        record("41. Phase 3 Regression: Login & JWT issuance works (200 OK)", r_login.status_code == 200 and "access_token" in r_login.json())

    finally:
        # Restore upload directory and cleanup isolated test uploads
        settings.UPLOAD_DIR = orig_upload_dir
        try:
            shutil.rmtree(temp_upload_dir, ignore_errors=True)
        except Exception:
            pass
        # Cleanup temporary test database
        try:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except Exception:
            pass

    print("\n" + "=" * 70)
    print(f"PHASE 4 VERIFICATION SUMMARY: Passed: {passed} | Failed: {failed}")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
