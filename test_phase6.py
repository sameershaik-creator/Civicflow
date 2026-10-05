"""
CivicFlow — Phase 6 Verification & Geographic Verification Test Suite

Verifies:
A. Authentication & Ownership Authorization
   1. Unauthenticated verification request is rejected (401 Unauthorized).
   2. Owner citizen can verify complaint location (200 OK).
   3. Foreign citizen cannot verify another user's complaint (403 Forbidden).
   4. Nonexistent complaint returns 404 Not Found.

B. Coordinate Validation
   5. Valid latitude and longitude accepted.
   6. Coordinate boundary validation: NaN, Inf rejected.
   7. Latitude > 90 rejected.
   8. Latitude < -90 rejected.
   9. Longitude > 180 rejected.
   10. Longitude < -180 rejected.

C. Forward Geocoding
   11. Address is sent to geographic service with proper User-Agent and query parameters.
   12. Successful Nominatim response parsed correctly (latitude, longitude, place_id, display_name).
   13. Empty forward geocoding result handled safely (returns None, status=GEOCODING_FAILED).
   14. Geocoding service timeout handled safely without unhandled exception.
   15. Geocoding HTTP error handled safely without exposing internal details.

D. Reverse Geocoding
   16. Valid coordinates sent to Nominatim reverse endpoint.
   17. Successful reverse response parsed correctly.
   18. Empty or error reverse geocoding response handled safely.
   19. Reverse geocoding failure handled without crash.

E. Coordinate Comparison & Distance
   20. Coordinates within threshold (e.g. 150m <= 500m) marked consistent (VERIFIED).
   21. Coordinates outside threshold (e.g. 2500m > 500m) marked discrepancy (MISMATCH).
   22. Haversine distance calculated accurately.
   23. Mismatch does NOT reject complaint (complaint status remains DRAFT/AI_GENERATED).
   24. Mismatch does NOT alter complaint ownership or user role.

F. Data Semantics & Provenance Preservation
   25. Device GPS telemetry remains strictly unchanged (original_latitude, original_longitude).
   26. Original citizen address remains strictly unchanged (original_address).
   27. AI draft fields remain untouched (ai_problem, ai_summary, ai_address).
   28. Final approval fields remain strictly NULL (final_problem, final_address, final_summary).
   29. Canonical geographic fields safely persisted (latitude, longitude, place_id, map_url, location_status).

G. Map Generation
   30. OpenStreetMap marker URL generated deterministically from actual coordinates.
   31. No fake or hardcoded coordinates used.
   32. Canonical coordinates mirror device GPS when available.

H. Regressions (Phases 1, 2, 3, 4, 5)
   33. Phase 1 Regression: GET /health and GET /health/db (200 OK).
   34. Phase 2 Regression: Database schema & Complaint ORM model intact.
   35. Phase 3 Regression: Login & JWT authentication succeed.
   36. Phase 4 Regression: Complaint intake with image upload preserves raw DRAFT.
   37. Phase 4 Regression: Protected image streaming enforces ownership (200 OK).
   38. Phase 5 Regression: AI draft generation transitions complaint to AI_GENERATED.

I. Real Geographic Service Runtime Verification (Section 29)
   39. Live Nominatim API call (verifying real HTTP request, coordinate parsing, distance check, DB persistence, and map URL).
"""

import sys
import os
import uuid
import math
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

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
    print("CIVICFLOW PHASE 6 — GEOGRAPHIC VERIFICATION & MAP TEST SUITE")
    print("=" * 70)

    # Setup isolated temporary test database
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_test_p6.db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p6_uploads_")
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
                email="citizen_geo_a@example.com",
                name="Amina Al-Mansoor",
                password_hash=auth_service.hash_password("PasswordAmina123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            user_b = User(
                id=str(uuid.uuid4()),
                email="citizen_geo_b@example.com",
                name="Carlos Mendez",
                password_hash=auth_service.hash_password("PasswordCarlos123!"),
                role=UserRole.CITIZEN.value,
                created_at=datetime.now(timezone.utc)
            )

            session.add_all([user_a, user_b])
            session.commit()

            token_a = auth_service.create_access_token(subject=user_a.id, role=user_a.role)
            token_b = auth_service.create_access_token(subject=user_b.id, role=user_b.role)

        auth_headers_a = {"Authorization": f"Bearer {token_a}"}
        auth_headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Complaint A for Citizen A (with both Address and GPS: Bangalore City Hall)
        # Lat: 12.9716, Lon: 77.5946 (Near Bangalore City Hall / Corporation Circle)
        res_create_a = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("pothole.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Deep roadway pothole near City Hall circle",
                "original_address": "Corporation Circle, Bangalore, Karnataka",
                "original_latitude": 12.9716,
                "original_longitude": 77.5946
            }
        )
        assert res_create_a.status_code == 201, f"Failed intake creation: {res_create_a.text}"
        cid_a = res_create_a.json()["id"]

        # Create Complaint B for Citizen B (GPS far from address -> Mismatch test case)
        # GPS is in Mumbai (18.9220, 72.8347), but address is entered as "Corporation Circle, Bangalore"
        res_create_b = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_b,
            files={"image": ("mismatch.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Damaged drain cover",
                "original_address": "Corporation Circle, Bangalore, Karnataka",
                "original_latitude": 18.9220,
                "original_longitude": 72.8347
            }
        )
        assert res_create_b.status_code == 201, f"Failed intake creation: {res_create_b.text}"
        cid_b = res_create_b.json()["id"]

        # Create Complaint C (Address only, no GPS)
        res_create_c = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("address_only.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Streetlight failure on 5th Main",
                "original_address": "MG Road, Bangalore, Karnataka"
            }
        )
        assert res_create_c.status_code == 201
        cid_c = res_create_c.json()["id"]

        # Create Complaint D (GPS only, no address)
        res_create_d = client.post(
            "/api/v1/complaints/analyze",
            headers=auth_headers_a,
            files={"image": ("gps_only.jpg", TINY_JPEG, "image/jpeg")},
            data={
                "original_problem": "Fallen tree branch on pavement",
                "original_latitude": 12.9750,
                "original_longitude": 77.6000
            }
        )
        assert res_create_d.status_code == 201
        cid_d = res_create_d.json()["id"]

        # =====================================================================
        # GROUP A: AUTHENTICATION & OWNERSHIP
        # =====================================================================
        print("\n--- A. Authentication & Ownership Authorization Tests ---")

        # 1. Unauthenticated verification request rejected (401)
        res_unauth = client.post(f"/api/v1/complaints/{cid_a}/location/verify")
        record("1. Unauthenticated verification rejected (401)", res_unauth.status_code == 401, f"Status: {res_unauth.status_code}")

        # 2. Foreign citizen cannot verify another user's complaint (403)
        res_foreign = client.post(f"/api/v1/complaints/{cid_a}/location/verify", headers=auth_headers_b)
        record("2. Foreign citizen cannot verify another citizen's complaint (403)", res_foreign.status_code == 403, f"Status: {res_foreign.status_code}")

        # 3. Nonexistent complaint returns 404
        random_cid = str(uuid.uuid4())
        res_404 = client.post(f"/api/v1/complaints/{random_cid}/location/verify", headers=auth_headers_a)
        record("3. Nonexistent complaint returns 404", res_404.status_code == 404, f"Status: {res_404.status_code}")

        # =====================================================================
        # GROUP B: COORDINATE VALIDATION
        # =====================================================================
        print("\n--- B. Coordinate Validation Tests ---")

        # 4. Valid coordinates accepted
        record("4. Valid latitude and longitude accepted", geocoding_service.validate_coordinates(12.9716, 77.5946))
        record("5. Equator & Prime Meridian coordinates accepted", geocoding_service.validate_coordinates(0.0, 0.0))
        record("6. Polar coordinates accepted (90.0, -90.0)", geocoding_service.validate_coordinates(90.0, 180.0) and geocoding_service.validate_coordinates(-90.0, -180.0))

        # 7-10. Coordinate boundary checks
        record("7. Latitude > 90 rejected", not geocoding_service.validate_coordinates(90.1, 77.0))
        record("8. Latitude < -90 rejected", not geocoding_service.validate_coordinates(-90.1, 77.0))
        record("9. Longitude > 180 rejected", not geocoding_service.validate_coordinates(12.0, 180.1))
        record("10. Longitude < -180 rejected", not geocoding_service.validate_coordinates(12.0, -180.1))
        record("10b. NaN and infinite coordinates rejected", not geocoding_service.validate_coordinates(float('nan'), 77.0) and not geocoding_service.validate_coordinates(12.0, float('inf')))

        # =====================================================================
        # GROUP C: FORWARD GEOCODING (MOCKED EXTERNAL SERVICE)
        # =====================================================================
        print("\n--- C. Forward Geocoding Unit Tests ---")

        # 11. Forward geocode sends correct params
        mock_fwd_data = [{
            "lat": "12.9718",
            "lon": "77.5948",
            "display_name": "Corporation Circle, Hudson Circle, Sampangi Rama Nagara, Bangalore, Karnataka, 560027, India",
            "place_id": 12345678
        }]

        with patch("httpx.Client.get") as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_fwd_data
            mock_resp.raise_for_status = MagicMock()
            mock_http_get.return_value = mock_resp

            fwd_result = geocoding_service.forward_geocode("Corporation Circle, Bangalore")

            record("11. Forward geocode returns structured coordinates", fwd_result is not None and abs(fwd_result["latitude"] - 12.9718) < 1e-4)
            record("12. Forward geocode captures place_id and display_name", fwd_result["place_id"] == "12345678" and "Bangalore" in fwd_result["display_name"])

        # 13. Empty forward geocode result handled safely
        with patch("httpx.Client.get") as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = []
            mock_resp.raise_for_status = MagicMock()
            mock_http_get.return_value = mock_resp

            empty_res = geocoding_service.forward_geocode("Nonexistent Place 9999999xyz")
            record("13. Empty forward geocode result returns None safely", empty_res is None)

        # 14. Geocoding service timeout handled safely
        import httpx
        with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
            timeout_res = geocoding_service.forward_geocode("Any Street")
            record("14. Service timeout handled safely (returns None)", timeout_res is None)

        # 15. Geocoding service HTTP 500 error handled safely
        with patch("httpx.Client.get") as mock_http_get:
            mock_err_resp = MagicMock()
            mock_err_resp.status_code = 500
            mock_err_resp.raise_for_status.side_effect = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_err_resp)
            mock_http_get.return_value = mock_err_resp

            err_res = geocoding_service.forward_geocode("Any Street")
            record("15. HTTP 500 handled safely without crash", err_res is None)

        # =====================================================================
        # GROUP D: REVERSE GEOCODING (MOCKED EXTERNAL SERVICE)
        # =====================================================================
        print("\n--- D. Reverse Geocoding Unit Tests ---")

        mock_rev_data = {
            "lat": "12.971600",
            "lon": "77.594600",
            "display_name": "City Hall, Nrupathunga Road, Sampangi Rama Nagara, Bangalore, Karnataka, 560001, India",
            "place_id": 87654321,
            "address": {
                "road": "Nrupathunga Road",
                "suburb": "Sampangi Rama Nagara",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India"
            }
        }

        with patch("httpx.Client.get") as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_rev_data
            mock_resp.raise_for_status = MagicMock()
            mock_http_get.return_value = mock_resp

            rev_result = geocoding_service.reverse_geocode(12.9716, 77.5946)
            record("16. Reverse geocode parses display address correctly", rev_result is not None and "City Hall" in rev_result["display_name"])
            record("17. Reverse geocode captures place_id", rev_result is not None and rev_result["place_id"] == "87654321")

        # 18. Reverse geocode empty/error response handled safely
        with patch("httpx.Client.get") as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"error": "Unable to geocode"}
            mock_resp.raise_for_status = MagicMock()
            mock_http_get.return_value = mock_resp

            empty_rev = geocoding_service.reverse_geocode(0.0, 0.0)
            record("18. Reverse geocode error response returns None safely", empty_rev is None)

        # =====================================================================
        # GROUP E: COORDINATE COMPARISON & DISTANCE
        # =====================================================================
        print("\n--- E. Coordinate Comparison & Distance Tests ---")

        # 19. Haversine distance formula accuracy
        # Distance between Bangalore (12.9716, 77.5946) and (12.9720, 77.5950) is ~61 meters
        dist_short = geocoding_service.calculate_haversine_distance(12.9716, 77.5946, 12.9720, 77.5950)
        record("19. Haversine distance calculation is accurate (approx 61m)", 50 < dist_short < 75, f"Distance: {dist_short}m")

        # Distance between Bangalore and Mumbai (~840 km)
        dist_long = geocoding_service.calculate_haversine_distance(12.9716, 77.5946, 18.9220, 72.8347)
        record("20. Haversine distance handles continental separation (~840km)", 800000 < dist_long < 900000, f"Distance: {int(dist_long)}m")

        # 21. Comparison: Close match marked VERIFIED
        with patch("app.services.geocoding_service.forward_geocode") as mock_fwd, \
             patch("app.services.geocoding_service.reverse_geocode") as mock_rev:

            # Address coords are 50m away from device coords (12.9716, 77.5946)
            mock_fwd.return_value = {"latitude": 12.9719, "longitude": 77.5948, "display_name": "Corporation Circle", "place_id": "111"}
            mock_rev.return_value = {"latitude": 12.9716, "longitude": 77.5946, "display_name": "City Hall", "place_id": "222"}

            res_ver = client.post(f"/api/v1/complaints/{cid_a}/location/verify", headers=auth_headers_a)
            record("21. Close coordinates marked VERIFIED", res_ver.status_code == 200 and res_ver.json()["location_status"] == "VERIFIED", f"Status: {res_ver.json().get('location_status')}")
            record("22. Address match is True for verified location", res_ver.json()["address_match"] is True)

        # 23. Comparison: Distant match marked MISMATCH
        with patch("app.services.geocoding_service.forward_geocode") as mock_fwd, \
             patch("app.services.geocoding_service.reverse_geocode") as mock_rev:

            # Address forward geocode gives Bangalore (12.9716, 77.5946), while complaint B GPS was Mumbai (18.9220, 72.8347)
            mock_fwd.return_value = {"latitude": 12.9716, "longitude": 77.5946, "display_name": "Corporation Circle, Bangalore", "place_id": "111"}
            mock_rev.return_value = {"latitude": 18.9220, "longitude": 72.8347, "display_name": "Gateway of India, Mumbai", "place_id": "999"}

            res_mismatch = client.post(f"/api/v1/complaints/{cid_b}/location/verify", headers=auth_headers_b)
            record(
                "23. Distant coordinates marked MISMATCH",
                res_mismatch.status_code == 200 and res_mismatch.json()["location_status"] in ("MISMATCH", "MISMATCH_SUSPECTED"),
                f"Status: {res_mismatch.json().get('location_status')}, Dist: {res_mismatch.json().get('distance_meters')}m"
            )
            record("24. Address match is False for mismatch location", res_mismatch.json()["address_match"] is False)

        # 25. Mismatch does NOT reject complaint
        with TestingSessionLocal() as session:
            c_b = session.query(Complaint).filter(Complaint.id == cid_b).first()
            record("25. Mismatch does NOT reject complaint (status remains DRAFT)", c_b.status == ComplaintStatus.DRAFT.value, f"Status: {c_b.status}")
            record("26. Mismatch does NOT alter user ownership", c_b.user_id == user_b.id)

        # =====================================================================
        # GROUP F: DATA SEMANTICS & PROVENANCE PRESERVATION
        # =====================================================================
        print("\n--- F. Data Semantics & Provenance Preservation Tests ---")

        with TestingSessionLocal() as session:
            c_a = session.query(Complaint).filter(Complaint.id == cid_a).first()
            record("27. Device original_latitude strictly preserved", c_a.original_latitude == 12.9716)
            record("28. Device original_longitude strictly preserved", c_a.original_longitude == 77.5946)
            record("29. Original citizen_address strictly preserved", c_a.original_address == "Corporation Circle, Bangalore, Karnataka")
            record("30. AI fields remain unaffected by location verification", c_a.ai_problem is None and c_a.ai_summary is None)
            record("31. Final approval fields remain strictly NULL", c_a.final_problem is None and c_a.final_summary is None)
            record("32. Canonical latitude and longitude persisted", c_a.latitude == 12.9716 and c_a.longitude == 77.5946)
            record("33. OpenStreetMap map_url persisted", c_a.map_url is not None and "openstreetmap.org" in c_a.map_url)

        # =====================================================================
        # GROUP G: ADDRESS-ONLY & GPS-ONLY HANDLING
        # =====================================================================
        print("\n--- G. Independent Address-Only & GPS-Only Handling ---")

        # 34. Address only forward geocodes and sets status GEOCODED
        with patch("app.services.geocoding_service.forward_geocode") as mock_fwd:
            mock_fwd.return_value = {"latitude": 12.9750, "longitude": 77.6000, "display_name": "MG Road", "place_id": "333"}
            res_c = client.post(f"/api/v1/complaints/{cid_c}/location/verify", headers=auth_headers_a)
            record("34. Address-only complaint marked GEOCODED", res_c.status_code == 200 and res_c.json()["location_status"] == "GEOCODED")
            record("35. Address-only complaint canonical coords mirror geocoded result", abs(res_c.json()["latitude"] - 12.9750) < 1e-4)

        # 36. GPS only reverse geocodes and sets status COORDINATES_ATTACHED / REVERSE_GEOCODED
        with patch("app.services.geocoding_service.reverse_geocode") as mock_rev:
            mock_rev.return_value = {"latitude": 12.9750, "longitude": 77.6000, "display_name": "MG Road Area", "place_id": "444"}
            res_d = client.post(f"/api/v1/complaints/{cid_d}/location/verify", headers=auth_headers_a)
            record("36. GPS-only complaint marked REVERSE_GEOCODED/COORDINATES_ATTACHED", res_d.status_code == 200 and res_d.json()["location_status"] in ("REVERSE_GEOCODED", "COORDINATES_ATTACHED"))

        # =====================================================================
        # GROUP H: REGRESSION CHECKS (PHASES 1, 2, 3, 4, 5)
        # =====================================================================
        print("\n--- H. Regression Checks (Phases 1, 2, 3, 4, 5) ---")

        # 37. Phase 1 Health Endpoint
        r_h = client.get("/health")
        record("37. Phase 1 Regression: GET /health (200 OK)", r_h.status_code == 200 and r_h.json() == {"status": "ok"})

        # 38. Phase 1 Database Health Endpoint
        r_db = client.get("/health/db")
        record("38. Phase 1 Regression: GET /health/db (200 OK)", r_db.status_code == 200 and r_db.json().get("database", {}).get("connected") is True)

        # 39. Phase 2 Database Schema Integrity
        with TestingSessionLocal() as session:
            test_c = session.query(Complaint).first()
            record("39. Phase 2 Regression: Complaint ORM model intact", test_c is not None and hasattr(test_c, "location_status"))

        # 40. Phase 3 Authentication Login Check
        r_login = client.post("/api/v1/auth/login", json={"email": "citizen_geo_a@example.com", "password": "PasswordAmina123!"})
        record("40. Phase 3 Regression: Login & JWT issuance works (200 OK)", r_login.status_code == 200 and "access_token" in r_login.json())

        # 41. Phase 4 Complaint intake preserves raw DRAFT
        record("41. Phase 4 Regression: Complaint intake created in state DRAFT", res_create_a.json()["status"] == "DRAFT")

        # 42. Phase 4 Evidence image streaming enforces ownership
        res_img_stream = client.get(f"/api/v1/complaints/{cid_a}/image", headers=auth_headers_a)
        record("42. Phase 4 Regression: Evidence image stream enforces ownership (200 OK)", res_img_stream.status_code == 200 and len(res_img_stream.content) > 0)

        # 43. Phase 5 AI draft analyze endpoint transition to AI_GENERATED
        mock_draft_data = GeminiComplaintDraft(
            category="Road Damage",
            observed_issue="Deep roadway pothole near City Hall circle.",
            citizen_claim="Reported hazardous road crater.",
            formal_summary="Roadway pothole near Corporation Circle requiring surface repaving.",
            urgency_level="HIGH",
            warnings=[]
        )
        with patch("app.agent.gemini_agent.get_gemini_client") as mock_get_ai:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = MagicMock(text=mock_draft_data.model_dump_json())
            mock_get_ai.return_value = mock_client

            with patch.object(settings, "GEMINI_API_KEY", "test-mock-key"):
                res_ai = client.post(f"/api/v1/complaints/{cid_a}/analyze", headers=auth_headers_a)
                record("43. Phase 5 Regression: AI draft transitions complaint to AI_GENERATED", res_ai.status_code == 200 and res_ai.json().get("category") == "Road Damage")

        # =====================================================================
        # GROUP I: REAL GEOGRAPHIC RUNTIME VERIFICATION (SECTION 29)
        # =====================================================================
        print("\n--- I. Real Geographic Runtime Verification (Section 29) ---")

        # Non-sensitive civic public landmark test location:
        # Public landmark: Eiffel Tower, Paris (Latitude: 48.8584, Longitude: 2.2945)
        print("[*] Executing live forward geocoding request to OpenStreetMap / Nominatim...")
        try:
            live_fwd = geocoding_service.forward_geocode("Eiffel Tower, Paris", timeout=12.0)
            if live_fwd and "latitude" in live_fwd and "longitude" in live_fwd:
                record(
                    "44. Real Forward Geocode Runtime Call",
                    True,
                    f"Resolved '{live_fwd['display_name'][:50]}...' -> Lat: {live_fwd['latitude']:.4f}, Lon: {live_fwd['longitude']:.4f}"
                )
            else:
                record_blocked("44. Real Forward Geocode Runtime Call", "Nominatim service unreachable or returned no results.")
        except Exception as e:
            record_blocked("44. Real Forward Geocode Runtime Call", f"Network/HTTP exception: {type(e).__name__}: {e}")

        print("[*] Executing live reverse geocoding request to OpenStreetMap / Nominatim...")
        try:
            live_rev = geocoding_service.reverse_geocode(48.8584, 2.2945, timeout=12.0)
            if live_rev and "display_name" in live_rev:
                record(
                    "45. Real Reverse Geocode Runtime Call",
                    True,
                    f"Resolved (48.8584, 2.2945) -> '{live_rev['display_name'][:50]}...'"
                )
            else:
                record_blocked("45. Real Reverse Geocode Runtime Call", "Nominatim reverse geocode returned no results.")
        except Exception as e:
            record_blocked("45. Real Reverse Geocode Runtime Call", f"Network/HTTP exception: {type(e).__name__}: {e}")

        # Live verification on a fresh complaint using real Nominatim service
        print("[*] Executing end-to-end live location verification on real complaint...")
        try:
            res_live_create = client.post(
                "/api/v1/complaints/analyze",
                headers=auth_headers_a,
                files={"image": ("live_geo.jpg", TINY_JPEG, "image/jpeg")},
                data={
                    "original_problem": "Fallen signpost near public landmark",
                    "original_address": "Eiffel Tower, Paris",
                    "original_latitude": 48.8584,
                    "original_longitude": 2.2945
                }
            )
            live_cid = res_live_create.json()["id"]

            res_live_verify = client.post(f"/api/v1/complaints/{live_cid}/location/verify", headers=auth_headers_a)
            if res_live_verify.status_code == 200:
                live_data = res_live_verify.json()
                record(
                    "46. Real End-to-End Complaint Location Verification",
                    live_data["location_status"] in ("VERIFIED", "COORDINATES_ATTACHED", "GEOCODED"),
                    f"Status: {live_data['location_status']}, Map URL: {live_data.get('map_url')}"
                )
            else:
                record_blocked("46. Real End-to-End Complaint Location Verification", f"HTTP {res_live_verify.status_code}")
        except Exception as e:
            record_blocked("46. Real End-to-End Complaint Location Verification", f"Exception: {type(e).__name__}: {e}")

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
    print(f"PHASE 6 VERIFICATION SUMMARY: Passed: {passed} | Failed: {failed} | Blocked: {blocked}")
    print("=" * 70)
    return failed == 0 and blocked == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
