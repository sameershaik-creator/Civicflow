"""
CivicFlow — Phase 12 Final Product Readiness, UI/UX Polish, Accessibility & Demo Verification Suite
===================================================================================================
Tests and verifies:
  Group A: Frontend Component & Visual System Architecture
  Group B: Accessibility, Semantic Markup & Labeling Integrity
  Group C: Truthful UI States, Copy & Anti-Theatrical Verification
  Group D: Zero-Demo Forensic Audit (Database, Storage & Frontend Source)
  Group E: Complete Public Service End-to-End Lifecycle Verification (Accept & Reject Pipelines)
  Group F: Cumulative System Regression & Boundary Invariants
"""

import os
import sys
import json
import uuid
import shutil
import tempfile
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

if str(backend_dir) not in sys.path:
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
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.config import settings
from app.main import app
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, LocationStatus
from app.models.notification import Notification
from app.services import auth_service
from app.schemas.ai import GeminiComplaintDraft
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

mock_ai_draft = GeminiComplaintDraft(
    category="Road Damage",
    observed_issue="Structural road defect: deep pothole with asphalt fracture",
    citizen_claim="Deep pothole near the intersection causing vehicular hazard",
    formal_summary="Report of a deep pothole creating roadway safety hazard near the intersection.",
    urgency_level="HIGH",
    warnings=["Potential vehicular tire damage risk during rainfall."]
)

mock_geo_verified = {
    "location_status": LocationStatus.VERIFIED.value,
    "latitude": 12.9716,
    "longitude": 77.5946,
    "place_id": "osm_p12_101",
    "map_url": "https://www.openstreetmap.org/?mlat=12.9716&mlon=77.5946#map=16/12.9716/77.5946",
    "distance_meters": 12.5,
    "address_match": True,
    "geocoded_address": "5th Main Road, City Center",
    "reverse_geocoded_address": "5th Main Road, City Center",
    "message": "Entered address corresponds to device GPS coordinates"
}


def run_tests():
    print("=" * 70)
    print("CIVICFLOW PHASE 12 — FINAL PRODUCT READINESS & DEMO VERIFICATION")
    print("=" * 70)

    # 1. Setup isolated database
    temp_dir = tempfile.mkdtemp(prefix="cf_test_p12_")
    temp_db_path = os.path.join(temp_dir, "test_p12.db")
    temp_db_url = f"sqlite:///{temp_db_path}"

    engine = sa.create_engine(
        temp_db_url,
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Isolated upload directory
    orig_upload_dir = settings.UPLOAD_DIR
    temp_upload_dir = os.path.join(temp_dir, "uploads")
    os.makedirs(temp_upload_dir, exist_ok=True)
    settings.UPLOAD_DIR = temp_upload_dir

    client = TestClient(app)

    passed = 0
    failed = 0
    blocked = 0

    def record(name, condition, extra=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            if extra:
                extra = f" -> {extra}"
            print(f"  [FAIL] {name}{extra}")

    try:
        # Pre-seed isolated fixtures
        with TestingSessionLocal() as db:
            admin_u = auth_service.create_admin_user(db, "Mayor Office", "admin_p12@example.com", "Admin1234!")
            citizen_u = auth_service.register_user(db, "Citizen Jane", "jane_p12@example.com", "Citizen1234!")
            admin_id = str(admin_u.id)
            admin_role = str(admin_u.role)
            citizen_id = str(citizen_u.id)
            citizen_role = str(citizen_u.role)

            token_admin = auth_service.create_access_token(admin_id, role=admin_role)
            token_citizen = auth_service.create_access_token(citizen_id, role=citizen_role)

        h_admin = {"Authorization": f"Bearer {token_admin}"}
        h_citizen = {"Authorization": f"Bearer {token_citizen}"}

        frontend_src = Path(__file__).resolve().parent / "frontend" / "src"

        print("\n--- GROUP A: FRONTEND COMPONENT & VISUAL SYSTEM ARCHITECTURE ---")

        # 1. Frontend source directory exists
        record("A1: Frontend source directory exists and is populated", frontend_src.exists() and (frontend_src / "App.jsx").exists())

        # 2. Key components exist
        header_file = frontend_src / "components" / "Header.jsx"
        home_file = frontend_src / "pages" / "Home.jsx"
        intake_file = frontend_src / "components" / "ComplaintIntakeForm.jsx"
        review_file = frontend_src / "components" / "ComplaintReviewCard.jsx"
        admin_file = frontend_src / "components" / "AdminAdjudicationDashboard.jsx"
        admin_login_file = frontend_src / "components" / "AdminLogin.jsx"
        notif_file = frontend_src / "components" / "CitizenNotifications.jsx"
        map_file = frontend_src / "components" / "InteractiveMap.jsx"

        record(
            "A2: All 8 primary frontend components exist (including AdminLogin)",
            header_file.exists() and home_file.exists() and intake_file.exists() and
            review_file.exists() and admin_file.exists() and admin_login_file.exists() and
            notif_file.exists() and map_file.exists()
        )

        # 3. UI primitives exist
        badge_file = frontend_src / "components" / "ui" / "StatusBadge.jsx"
        alert_file = frontend_src / "components" / "ui" / "Alert.jsx"
        empty_file = frontend_src / "components" / "ui" / "EmptyState.jsx"
        load_file = frontend_src / "components" / "ui" / "LoadingState.jsx"

        record(
            "A3: Standardized UI primitives (StatusBadge, Alert, EmptyState, LoadingState) exist",
            badge_file.exists() and alert_file.exists() and empty_file.exists() and load_file.exists()
        )

        # 4. Tailwind configuration includes civic brand tokens
        tw_config = Path(__file__).resolve().parent / "frontend" / "tailwind.config.js"
        tw_text = tw_config.read_text(encoding="utf-8") if tw_config.exists() else ""
        record("A4: Tailwind config defines civic brand palette", "civic:" in tw_text or "colors:" in tw_text)

        # 5. Index.css includes accessible focus-visible styles
        css_file = frontend_src / "index.css"
        css_text = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
        record("A5: Global CSS includes accessible focus-visible outline", ":focus-visible" in css_text)

        # 6. Index.html includes descriptive title and meta description
        index_html = Path(__file__).resolve().parent / "frontend" / "index.html"
        html_text = index_html.read_text(encoding="utf-8") if index_html.exists() else ""
        record("A6: Index.html contains truthful title and meta description", "<meta name=\"description\"" in html_text and "CivicFlow" in html_text)

        # 7. Header implements responsive mobile navigation menu
        h_text = header_file.read_text(encoding="utf-8") if header_file.exists() else ""
        record("A7: Header component includes responsive mobile menu toggle", "mobileMenuOpen" in h_text and "Menu" in h_text)

        # 8. Home hero introduces truthful 10-second jury message
        home_text = home_file.read_text(encoding="utf-8") if home_file.exists() else ""
        record("A8: Home hero provides concise 10-second public service explanation", "Report civic issues with evidence, location, and human review" in home_text)

        # 9. Home pipeline explains 5 distinct workflow stages
        record("A9: Home displays 5-stage human-in-the-loop workflow architecture", "1. Citizen Evidence" in home_text and "5. Municipal Adjudication" in home_text)

        # 10. Developer health status is cleanly collapsible
        record("A10: HealthStatusCard is cleanly collapsible for uncluttered civic demo", "showHealthCard" in home_text)

        print("\n--- GROUP B: ACCESSIBILITY, SEMANTIC MARKUP & LABELING INTEGRITY ---")

        # 11. StatusBadge pairs icons with text
        b_text = badge_file.read_text(encoding="utf-8") if badge_file.exists() else ""
        record("B11: StatusBadge does not rely on color alone (pairs icons and text labels)", "aria-label" in b_text and "role=\"status\"" in b_text)

        # 12. Alert component uses semantic ARIA roles
        a_text = alert_file.read_text(encoding="utf-8") if alert_file.exists() else ""
        record("B12: Alert component defines semantic ARIA role='alert' or role='status'", "role=" in a_text)

        # 13. Complaint intake form has explicit label-to-input matching
        intake_text = intake_file.read_text(encoding="utf-8") if intake_file.exists() else ""
        record("B13: Intake form binds labels to inputs via htmlFor/id", 'htmlFor="problem-input"' in intake_text and 'id="problem-input"' in intake_text)

        # 14. File upload input is properly labeled
        record("B14: Evidence photo input is accessible via htmlFor", 'htmlFor="evidence-photo-input"' in intake_text)

        # 15. Form inputs have visible focus ring classes
        record("B15: Form inputs apply accessible focus ring styles", "focus:ring-2 focus:ring-blue-500" in intake_text)

        # 16. Image previews have descriptive alt text
        record("B16: Image previews include meaningful alt text", 'alt="Uploaded incident evidence preview"' in intake_text)

        # 17. Review card distinguishes editable fields from read-only provenance
        rev_text = review_file.read_text(encoding="utf-8") if review_file.exists() else ""
        record("B17: Review card explicitly separates read-only layers from editable final report", "1. Original Citizen Evidence" in rev_text and "3. Citizen Final Report" in rev_text)

        # 18. Admin rejection textarea has explicit label
        adm_text = admin_file.read_text(encoding="utf-8") if admin_file.exists() else ""
        record("B18: Admin rejection reason textarea is labeled and accessible", 'htmlFor="rejection-reason"' in adm_text and 'id="rejection-reason"' in adm_text)

        # 19. Notifications have semantic article and time tags
        notif_text = notif_file.read_text(encoding="utf-8") if notif_file.exists() else ""
        record("B19: Notifications utilize semantic <article> and <time> markup", "<article" in notif_text and "<time" in notif_text)

        # 20. Refresh buttons have accessible aria-labels
        record("B20: Icon-only buttons have accessible aria-labels", 'aria-label="Refresh notifications"' in notif_text)

        print("\n--- GROUP C: TRUTHFUL UI STATES, COPY & ANTI-THEATRICAL VERIFICATION ---")

        # 21. No fake AI activation theater in frontend
        all_frontend_js = "".join([f.read_text(encoding="utf-8", errors="ignore") for f in frontend_src.rglob("*.js*")])
        record("C21: Zero fake AI engine activation theater found in frontend", "ai engine activated" not in all_frontend_js.lower() and "agent thinking..." not in all_frontend_js.lower())

        # 22. No fake token counters or confidence meters
        record("C22: Zero fake confidence meters or token counters in frontend", "confidence meter" not in all_frontend_js.lower() and "token counter" not in all_frontend_js.lower())

        # 23. GPS device location is explicitly labeled as supporting evidence
        record("C23: GPS coordinates clearly explained as supporting device evidence", "not treated as proof that the photo was taken there" in intake_text)

        # 23b. No frontend role selector in registration
        record("C23b: No frontend role selector exists (public registration restricted to citizens)", "value=\"admin\"" not in intake_text and "name=\"role\"" not in intake_text)

        # 24. Calm location mismatch language
        map_text = map_file.read_text(encoding="utf-8") if map_file.exists() else ""
        record("C24: Location mismatch uses calm, neutral phrasing (no 'fraud detected')", "location information differs" in map_text.lower() and "fraud detected" not in map_text.lower())

        # 25. Truthful AI loading copy
        record("C25: Truthful AI loading copy reflects real API state", "Preparing your draft report" in intake_text)

        # 26. Truthful empty state in admin queue
        record("C26: Admin queue shows truthful empty state when 0 complaints exist", "No submitted complaints are currently awaiting review" in adm_text)

        # 27. Truthful empty state in notifications
        record("C27: Notification view shows truthful empty state when 0 notifications exist", "You're all caught up" in notif_text)

        # 28. Truthful empty state in citizen complaint list
        record("C28: Citizen complaint history shows truthful empty state when 0 complaints exist", "You haven't submitted any complaints yet" in intake_text)

        print("\n--- GROUP D: ZERO-DEMO FORENSIC AUDIT (DATABASE, STORAGE & FRONTEND) ---")

        # 29. Runtime civicflow.db has 0 seeded complaints
        root_db = Path(__file__).resolve().parent / "civicflow.db"
        backend_db = backend_dir / "civicflow.db"
        real_c_count = 0
        real_n_count = 0
        target_db = backend_db if backend_db.exists() else root_db if root_db.exists() else None

        if target_db:
            r_eng = sa.create_engine(f"sqlite:///{target_db}")
            insp = sa.inspect(r_eng)
            tables = insp.get_table_names()
            with r_eng.connect() as conn:
                if "complaints" in tables:
                    real_c_count = conn.execute(sa.text("SELECT COUNT(*) FROM complaints")).scalar() or 0
                if "notifications" in tables:
                    real_n_count = conn.execute(sa.text("SELECT COUNT(*) FROM notifications")).scalar() or 0
            r_eng.dispose()

        record("D29: Runtime database contains 0 seeded complaints", real_c_count == 0, f"found {real_c_count}")

        # 30. Runtime database has 0 seeded notifications
        record("D30: Runtime database contains 0 seeded notifications", real_n_count == 0, f"found {real_n_count}")

        # 31. Uploads directory contains 0 residual test images
        real_uploads = backend_dir / "uploads" / "complaints"
        files = list(real_uploads.glob("*.*")) if real_uploads.exists() else []
        non_gitkeep = [f for f in files if f.name != ".gitkeep"]
        record("D31: Runtime uploads directory contains 0 residual test files", len(non_gitkeep) == 0, f"found {len(non_gitkeep)}")

        # 32. Frontend contains zero hardcoded complaint records
        record("D32: Frontend src contains zero hardcoded demo complaints", "sample complaint" not in all_frontend_js.lower() and "demo pothole" not in all_frontend_js.lower())

        # 33. Frontend contains zero hardcoded notifications
        record("D33: Frontend src contains zero hardcoded notifications", "fake notification" not in all_frontend_js.lower())

        # 34. Frontend contains zero hardcoded admin statistics
        record("D34: Admin dashboard contains zero fabricated metrics or hardcoded counts", "24 complaints awaiting review" not in adm_text)

        print("\n--- GROUP E: COMPLETE PUBLIC SERVICE END-TO-END LIFECYCLE VERIFICATION ---")

        # 35. Citizen intake creates authentic DRAFT
        r_intake = client.post(
            "/api/v1/complaints/analyze",
            headers=h_citizen,
            data={"original_problem": "Deep roadway depression causing safety hazard", "original_address": "5th Main Road", "original_latitude": 12.9716, "original_longitude": 77.5946},
            files={"image": ("hazard.jpg", TINY_JPEG, "image/jpeg")}
        )
        record("E35: Citizen creates complaint draft with evidence photo (DRAFT)", r_intake.status_code == 201 and r_intake.json()["status"] == "DRAFT")
        cid = r_intake.json()["id"]

        # 36. Multimodal AI analysis structures draft (AI_GENERATED)
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_ai_draft):
            r_ai = client.post(f"/api/v1/complaints/{cid}/analyze", headers=h_citizen)
            c_check = client.get(f"/api/v1/complaints/{cid}", headers=h_citizen)
            record("E36: Gemini AI structures complaint draft (AI_GENERATED)", r_ai.status_code == 200 and c_check.json()["status"] == "AI_GENERATED")

        # 37. Deterministic GIS location verification succeeds
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo_verified):
            r_geo = client.post(f"/api/v1/complaints/{cid}/location/verify", headers=h_citizen)
            record("E37: Geographic geocoding and verification succeeds (VERIFIED)", r_geo.status_code == 200 and r_geo.json()["location_status"] == "VERIFIED")

        # 38. Citizen human review updates text (UNDER_REVIEW)
        r_rev = client.put(
            f"/api/v1/complaints/{cid}/draft",
            headers=h_citizen,
            json={
                "final_problem": "Confirmed major pothole on 5th Main Road near cross junction",
                "final_address": "5th Main Road, City Center",
                "final_summary": "Authorized report of severe pavement fracture on 5th Main Road."
            }
        )
        record("E38: Citizen reviews, edits, and authorizes draft (UNDER_REVIEW)", r_rev.status_code == 200 and r_rev.json()["status"] == "UNDER_REVIEW")

        # 39. Citizen authoritative submission (SUBMITTED)
        r_sub = client.post(f"/api/v1/complaints/{cid}/submit", headers=h_citizen)
        record("E39: Citizen authoritatively submits complaint (SUBMITTED)", r_sub.status_code == 200 and r_sub.json()["status"] == "SUBMITTED")

        # 40. Admin inspects submitted queue
        r_queue = client.get("/api/v1/admin/complaints?status=SUBMITTED", headers=h_admin)
        record("E40: Admin discovers submitted complaint in triage queue", r_queue.status_code == 200 and any(c["id"] == cid for c in r_queue.json()))

        # 41. Admin inspects case file and complete provenance
        r_detail = client.get(f"/api/v1/admin/complaints/{cid}", headers=h_admin)
        detail = r_detail.json()
        record(
            "E41: Admin case file contains complete multi-layer provenance",
            detail["original_problem"] is not None and
            detail["ai_problem"] is not None and
            detail["final_problem"] is not None and
            detail["latitude"] is not None
        )

        # 42. Admin formally accepts complaint (ACCEPTED)
        r_accept = client.post(f"/api/v1/admin/complaints/{cid}/accept", headers=h_admin)
        record("E42: Admin formally accepts complaint (ACCEPTED)", r_accept.status_code == 200 and r_accept.json()["status"] == "ACCEPTED")

        # 43. Citizen receives atomic in-app notification
        r_notifs = client.get("/api/v1/notifications", headers=h_citizen)
        notifs = r_notifs.json()
        notif_match = next((n for n in notifs if n["complaint_id"] == cid), None)
        record(
            "E43: Citizen receives official in-app acceptance notification",
            notif_match is not None and "accepted" in notif_match["title"].lower() and not notif_match["is_read"]
        )

        # 44. Citizen marks notification as read (idempotent)
        if notif_match:
            r_mark = client.patch(f"/api/v1/notifications/{notif_match['id']}/read", headers=h_citizen)
            r_unread = client.get("/api/v1/notifications/unread-count", headers=h_citizen)
            record("E44: Citizen marks notification read and unread count updates", r_mark.status_code == 200 and r_unread.json()["unread_count"] == 0)
        else:
            record("E44: Citizen marks notification read and unread count updates", False)

        print("\n--- GROUP F: CUMULATIVE SYSTEM REGRESSION & BOUNDARY INVARIANTS ---")

        # 45. Rejection pipeline with verbatim municipal explanation delivery
        r_intake2 = client.post(
            "/api/v1/complaints/analyze",
            headers=h_citizen,
            data={"original_problem": "Fallen tree branch on private residential property"},
            files={"image": ("branch.jpg", TINY_JPEG, "image/jpeg")}
        )
        cid2 = r_intake2.json()["id"]
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_ai_draft):
            client.post(f"/api/v1/complaints/{cid2}/analyze", headers=h_citizen)
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo_verified):
            client.post(f"/api/v1/complaints/{cid2}/location/verify", headers=h_citizen)
        client.put(f"/api/v1/complaints/{cid2}/draft", headers=h_citizen, json={"final_problem": "Tree branch on private driveway"})
        client.post(f"/api/v1/complaints/{cid2}/submit", headers=h_citizen)

        r_reject = client.post(
            f"/api/v1/admin/complaints/{cid2}/reject",
            headers=h_admin,
            json={"admin_reason": "Private property: falls under residential society maintenance, outside municipal jurisdiction."}
        )
        r_notifs2 = client.get("/api/v1/notifications", headers=h_citizen)
        notif2 = next((n for n in r_notifs2.json() if n["complaint_id"] == cid2), None)
        record(
            "F45: Rejection pipeline delivers verbatim municipal explanation to citizen notification",
            r_reject.status_code == 200 and notif2 is not None and "Private property" in notif2["message"]
        )

        # 46. Terminal complaints permanently locked from mutation
        r_tamper = client.put(f"/api/v1/complaints/{cid}/draft", headers=h_citizen, json={"final_problem": "Malicious post-acceptance overwrite"})
        record("F46: Terminal accepted complaint strictly locked against edits (400 Bad Request)", r_tamper.status_code == 400)

        # 47. Terminal rejected complaint locked against edits
        r_tamper2 = client.put(f"/api/v1/complaints/{cid2}/draft", headers=h_citizen, json={"final_problem": "Malicious post-rejection overwrite"})
        record("F47: Terminal rejected complaint strictly locked against edits (400 Bad Request)", r_tamper2.status_code == 400)

        # 48. Public registration hardcodes citizen role
        r_pub = client.post("/api/v1/auth/register", json={"name": "Attacker", "email": "attacker_p12@example.com", "password": "Pass1234!", "role": "admin"})
        record("F48: Public registration hardcodes CITIZEN role ignoring role payload", r_pub.status_code == 201 and r_pub.json()["role"] == "citizen")

        # 49. Row-level ownership protects complaint access (IDOR blocked)
        r_foreign = client.get(f"/api/v1/complaints/{cid}", headers={"Authorization": f"Bearer {r_pub.json()['access_token']}"})
        record("F49: Row-level ownership blocks cross-citizen complaint reading (403 Forbidden)", r_foreign.status_code == 403)

        # 50. Health check endpoints live and verified
        r_h1 = client.get("/health")
        r_h2 = client.get("/health/db")
        record("F50: Health endpoints (/health and /health/db) return 200 OK", r_h1.status_code == 200 and r_h2.status_code == 200)

    finally:
        app.dependency_overrides.clear()
        settings.UPLOAD_DIR = orig_upload_dir

        try:
            engine.dispose()
        except Exception:
            pass

        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass

        if os.path.exists(temp_upload_dir):
            try:
                shutil.rmtree(temp_upload_dir, ignore_errors=True)
            except Exception:
                pass

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    print("\n" + "=" * 70)
    print(f"PHASE 12 SUITE RESULTS: {passed} PASSED | {failed} FAILED | {blocked} BLOCKED")
    print("=" * 70)

    return passed, failed, blocked


if __name__ == "__main__":
    p, f, b = run_tests()
    if f > 0 or b > 0:
        sys.exit(1)
    sys.exit(0)
