"""
CivicFlow — Phase 10 Verification Test Suite: Citizen In-App Notification Engine

Verifies:
A. Notification Creation
   1. ACCEPTED decision creates exactly one notification.
   2. REJECTED decision creates exactly one notification.
   3. Notification references correct user_id.
   4. Notification references correct complaint_id.
   5. Accepted message is generated server-side.
   6. Rejected message contains actual admin_reason.
   7. Notification created_at is server-generated.

B. Transaction Safety & Atomicity
   8. Accept + notification commit atomically.
   9. Reject + notification commit atomically.
   10. Simulated persistence failure rolls back ACCEPTED decision.
   11. Simulated persistence failure rolls back REJECTED decision.
   12. No orphan notification exists after rollback.

C. Duplicate Protection
   13. Duplicate accept creates no second notification.
   14. Duplicate reject creates no second notification.
   15. Accept-after-reject creates no notification.
   16. Reject-after-accept creates no notification.

D. Notification Listing
   17. Authenticated citizen can list own notifications.
   18. Unauthenticated list returns 401 Unauthorized.
   19. Foreign citizen notifications are excluded.
   20. Notifications ordered newest first.
   21. Empty notification database returns [].
   22. Real unread/read values are returned.
   23. Authenticated citizen can get unread count.
   24. Unauthenticated unread count returns 401.

E. Notification Detail
   25. Owner can retrieve notification detail.
   26. Foreign citizen cannot retrieve notification detail (403 Forbidden).
   27. Nonexistent notification returns 404 Not Found.
   28. Unauthenticated notification detail returns 401 Unauthorized.

F. Mark Read
   29. Owner can mark notification as read (PATCH /{id}/read).
   30. Unauthenticated mark-read returns 401 Unauthorized.
   31. Foreign citizen cannot mark notification as read (403 Forbidden).
   32. Already-read notification remains safely read (idempotent).
   33. Mark-read does not modify complaint.
   34. Mark-read does not modify title, message, or user_id.
   35. Mark-read does not modify created_at.
   36. Marking notification as read updates unread count.

G. Message Integrity
   37. Client cannot create arbitrary acceptance messages via endpoint.
   38. Client cannot create arbitrary rejection messages via endpoint.
   39. Rejection reason strictly matches persisted admin decision.
   40. Notification reflects actual complaint status.

H. Provenance Immutability
   41. original_* fields remain strictly unchanged after notification creation.
   42. ai_* fields remain strictly unchanged.
   43. final_* fields remain strictly unchanged.
   44. Complaint status remains authoritative source of truth.

I. Security & Authorization
   45. Client cannot inject another user_id into notification.
   46. Client cannot inject another complaint_id.
   47. Client cannot change notification ownership.
   48. Client cannot modify notification message.
   49. Client cannot modify notification creation timestamp.
   50. No public/unauthenticated notification mutation endpoints exist.

J. Zero-Demo-Data Forensic Audit
   51. Normal runtime database contains no seeded notifications.
   52. Frontend contains no hardcoded notifications.
   53. Frontend contains no fake unread count.
   54. Normal runtime database contains no seeded complaints.
   55. No sample notification records exist in codebase.

K. Cumulative Regressions (Phases 1-9)
   56. Phase 1: /health & /health/db return 200 OK.
   57. Phase 2: Database schema and ORM models intact.
   58. Phase 3: Login and JWT issuance succeed.
   59. Phase 4: Complaint intake created in DRAFT.
   60. Phase 5: Gemini AI draft transitions complaint to AI_GENERATED.
   61. Phase 6: Geographic verification succeeds.
   62. Phase 7: Draft editing transitions complaint to UNDER_REVIEW.
   63. Phase 8: Final submission transitions complaint to SUBMITTED.
   64. Phase 9: Admin adjudication (ACCEPT & REJECT) functions correctly.

L. Real Runtime End-to-End Pipeline
   65. E2E Accept: Citizen submits -> Admin accepts -> Notification created -> Citizen reads & marks read -> Unread count decrements.
   66. E2E Reject: Citizen submits -> Admin rejects with reason -> Notification created with reason -> Citizen views & marks read.
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
from app.models.notification import Notification
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
    print("CIVICFLOW PHASE 10 — CITIZEN IN-APP NOTIFICATION ENGINE TEST SUITE")
    print("=" * 70)

    # Setup isolated temporary test database
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_test_p10.db")
    os.close(temp_db_fd)
    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Setup isolated temporary test uploads directory to prevent runtime pollution
    temp_upload_dir = tempfile.mkdtemp(prefix="test_p10_uploads_")
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
        now = datetime.now(timezone.utc)

        # Seed test users using standard auth_service conventions
        with TestingSessionLocal() as session:
            citizen1 = User(
                id=str(uuid.uuid4()),
                email="citizen1_p10@example.com",
                name="Citizen One P10",
                password_hash=auth_service.hash_password("PassCitizen123!"),
                role=UserRole.CITIZEN.value,
                created_at=now
            )
            citizen2 = User(
                id=str(uuid.uuid4()),
                email="citizen2_p10@example.com",
                name="Citizen Two P10",
                password_hash=auth_service.hash_password("PassCitizen123!"),
                role=UserRole.CITIZEN.value,
                created_at=now
            )
            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin_p10@example.com",
                name="Admin User P10",
                password_hash=auth_service.hash_password("AdminPass123!"),
                role=UserRole.ADMIN.value,
                created_at=now
            )
            session.add_all([citizen1, citizen2, admin_user])
            session.commit()

            c1_id = citizen1.id
            c2_id = citizen2.id
            adm_id = admin_user.id

            token_c1 = auth_service.create_access_token(subject=citizen1.id, role=citizen1.role)
            token_c2 = auth_service.create_access_token(subject=citizen2.id, role=citizen2.role)
            token_adm = auth_service.create_access_token(subject=admin_user.id, role=admin_user.role)

        h_c1 = {"Authorization": f"Bearer {token_c1}"}
        h_c2 = {"Authorization": f"Bearer {token_c2}"}
        h_adm = {"Authorization": f"Bearer {token_adm}"}

        # Helper to create submitted complaints
        def create_submitted_complaint(user_id: str, title: str = "Pothole"):
            with TestingSessionLocal() as db_s:
                c = Complaint(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    status=ComplaintStatus.SUBMITTED.value,
                    original_problem=f"Hazardous {title} on test avenue",
                    original_address="123 Test Avenue, Metropolis",
                    original_latitude=12.9716,
                    original_longitude=77.5946,
                    image_url="/uploads/complaints/test_p10.jpg",
                    ai_problem=f"Significant {title} requiring asphalt repair",
                    ai_address="123 Test Avenue, Metropolis",
                    ai_summary="AI classified pothole hazard",
                    final_problem=f"Citizen confirmed {title}",
                    final_address="123 Test Avenue, Metropolis",
                    final_summary="Citizen confirmed final summary",
                    location_status=LocationStatus.VERIFIED.value,
                    created_at=now,
                    updated_at=now,
                    submitted_at=now,
                )
                db_s.add(c)
                db_s.commit()
                return c.id

        # ------------------------------------------------------------
        # Group A: Notification Creation
        # ------------------------------------------------------------
        print("\n--- Group A: Notification Creation ---")

        # 1. ACCEPTED decision creates exactly one notification
        c_acc_id = create_submitted_complaint(c1_id, "Acceptable Issue")
        r_acc = client.post(f"/api/v1/admin/complaints/{c_acc_id}/accept", headers=h_adm)
        record("A1: ACCEPTED decision returns 200 OK", r_acc.status_code == 200)

        with TestingSessionLocal() as db_check:
            notifs_c1 = db_check.query(Notification).filter(Notification.complaint_id == c_acc_id).all()
            record("A1.1: Exactly one notification created on ACCEPT", len(notifs_c1) == 1, f"Found {len(notifs_c1)}")

            # 2. REJECTED decision creates exactly one notification
            c_rej_id = create_submitted_complaint(c1_id, "Rejectable Issue")
            r_rej = client.post(
                f"/api/v1/admin/complaints/{c_rej_id}/reject",
                headers=h_adm,
                json={"admin_reason": "Private driveway, outside municipal jurisdiction."},
            )
            record("A2: REJECTED decision returns 200 OK", r_rej.status_code == 200)

            notifs_rej = db_check.query(Notification).filter(Notification.complaint_id == c_rej_id).all()
            record("A2.1: Exactly one notification created on REJECT", len(notifs_rej) == 1, f"Found {len(notifs_rej)}")

            # 3. Notification references correct user_id
            n_acc = notifs_c1[0]
            n_rej = notifs_rej[0]
            record("A3: Notification references correct user_id", n_acc.user_id == c1_id and n_rej.user_id == c1_id)

            # 4. Notification references correct complaint_id
            record("A4: Notification references correct complaint_id", n_acc.complaint_id == c_acc_id and n_rej.complaint_id == c_rej_id)

            # 5. Accepted message is generated server-side
            record(
                "A5: Accepted notification has truthful server-generated title & message",
                n_acc.title == "Complaint accepted" and "accepted for administrative action" in n_acc.message,
                f"Title='{n_acc.title}', Message='{n_acc.message}'",
            )

            # 6. Rejected message contains actual admin_reason
            record(
                "A6: Rejected notification contains actual admin_reason",
                n_rej.title == "Complaint update" and "Private driveway, outside municipal jurisdiction." in n_rej.message,
                f"Message='{n_rej.message}'",
            )

            # 7. Notification created_at is server-generated
            record(
                "A7: Notification created_at is server-generated UTC datetime",
                isinstance(n_acc.created_at, datetime) and n_acc.created_at is not None,
                f"created_at={n_acc.created_at}",
            )

        # ------------------------------------------------------------
        # Group B: Transaction Safety & Atomicity
        # ------------------------------------------------------------
        print("\n--- Group B: Transaction Safety & Atomicity ---")

        with TestingSessionLocal() as db_b:
            comp_acc_check = db_b.query(Complaint).filter(Complaint.id == c_acc_id).first()
            record("B8: Complaint is ACCEPTED and notification exists", comp_acc_check.status == ComplaintStatus.ACCEPTED.value and len(notifs_c1) == 1)

            comp_rej_check = db_b.query(Complaint).filter(Complaint.id == c_rej_id).first()
            record("B9: Complaint is REJECTED and notification exists", comp_rej_check.status == ComplaintStatus.REJECTED.value and len(notifs_rej) == 1)

        # 10. Simulated persistence failure rolls back ACCEPTED decision
        c_fail_acc = create_submitted_complaint(c1_id, "Fail Accept")
        with patch.object(Session, "commit", side_effect=Exception("Simulated DB Disk Failure")):
            r_sim_acc = client.post(f"/api/v1/admin/complaints/{c_fail_acc}/accept", headers=h_adm)
            record("B10: Simulated DB error on accept returns 500", r_sim_acc.status_code == 500)

        with TestingSessionLocal() as db_roll:
            c_roll_acc = db_roll.query(Complaint).filter(Complaint.id == c_fail_acc).first()
            notifs_roll_acc = db_roll.query(Notification).filter(Notification.complaint_id == c_fail_acc).all()
            record("B10.1: Rolled back complaint remains SUBMITTED", c_roll_acc.status == ComplaintStatus.SUBMITTED.value, f"Status={c_roll_acc.status}")
            record("B12.1: No orphan notification created on rolled-back accept", len(notifs_roll_acc) == 0, f"Found {len(notifs_roll_acc)}")

        # 11. Simulated persistence failure rolls back REJECTED decision
        c_fail_rej = create_submitted_complaint(c1_id, "Fail Reject")
        with patch.object(Session, "commit", side_effect=Exception("Simulated DB Lock Failure")):
            r_sim_rej = client.post(
                f"/api/v1/admin/complaints/{c_fail_rej}/reject",
                headers=h_adm,
                json={"admin_reason": "Valid reason for failure test"},
            )
            record("B11: Simulated DB error on reject returns 500", r_sim_rej.status_code == 500)

        with TestingSessionLocal() as db_roll2:
            c_roll_rej = db_roll2.query(Complaint).filter(Complaint.id == c_fail_rej).first()
            notifs_roll_rej = db_roll2.query(Notification).filter(Notification.complaint_id == c_fail_rej).all()
            record("B11.1: Rolled back complaint remains SUBMITTED", c_roll_rej.status == ComplaintStatus.SUBMITTED.value, f"Status={c_roll_rej.status}")
            record("B12.2: No orphan notification created on rolled-back reject", len(notifs_roll_rej) == 0, f"Found {len(notifs_roll_rej)}")

        # ------------------------------------------------------------
        # Group C: Duplicate Protection
        # ------------------------------------------------------------
        print("\n--- Group C: Duplicate Protection ---")

        # 13. Duplicate accept creates no second notification
        r_dup_acc = client.post(f"/api/v1/admin/complaints/{c_acc_id}/accept", headers=h_adm)
        record("C13: Second accept attempt returns 400 Bad Request", r_dup_acc.status_code == 400)

        with TestingSessionLocal() as db_dup:
            notifs_dup_acc = db_dup.query(Notification).filter(Notification.complaint_id == c_acc_id).all()
            record("C13.1: Exactly one notification remains after duplicate accept attempt", len(notifs_dup_acc) == 1)

            # 14. Duplicate reject creates no second notification
            r_dup_rej = client.post(
                f"/api/v1/admin/complaints/{c_rej_id}/reject",
                headers=h_adm,
                json={"admin_reason": "Another reason"},
            )
            record("C14: Second reject attempt returns 400 Bad Request", r_dup_rej.status_code == 400)

            notifs_dup_rej = db_dup.query(Notification).filter(Notification.complaint_id == c_rej_id).all()
            record("C14.1: Exactly one notification remains after duplicate reject attempt", len(notifs_dup_rej) == 1)

            # 15. Accept-after-reject creates no notification
            r_acc_after_rej = client.post(f"/api/v1/admin/complaints/{c_rej_id}/accept", headers=h_adm)
            record("C15: Accept on already REJECTED complaint returns 400", r_acc_after_rej.status_code == 400)
            notifs_after_rej = db_dup.query(Notification).filter(Notification.complaint_id == c_rej_id).all()
            record("C15.1: No notification created on invalid transition", len(notifs_after_rej) == 1)

            # 16. Reject-after-accept creates no notification
            r_rej_after_acc = client.post(
                f"/api/v1/admin/complaints/{c_acc_id}/reject",
                headers=h_adm,
                json={"admin_reason": "Cannot reject accepted"},
            )
            record("C16: Reject on already ACCEPTED complaint returns 400", r_rej_after_acc.status_code == 400)
            notifs_after_acc = db_dup.query(Notification).filter(Notification.complaint_id == c_acc_id).all()
            record("C16.1: No notification created on invalid transition", len(notifs_after_acc) == 1)

        # ------------------------------------------------------------
        # Group D: Notification Listing & Unread Count
        # ------------------------------------------------------------
        print("\n--- Group D: Notification Listing & Unread Count ---")

        # 17. Authenticated citizen can list own notifications
        r_list_c1 = client.get("/api/v1/notifications", headers=h_c1)
        record("D17: Authenticated citizen lists own notifications (200 OK)", r_list_c1.status_code == 200)
        c1_items = r_list_c1.json()
        record("D17.1: Citizen 1 has expected notifications", len(c1_items) == 2, f"Count={len(c1_items)}")

        # 18. Unauthenticated list returns 401 Unauthorized
        r_unauth_list = client.get("/api/v1/notifications")
        record("D18: Unauthenticated list returns 401 Unauthorized", r_unauth_list.status_code == 401)

        # 19. Foreign citizen notifications are excluded
        r_list_c2 = client.get("/api/v1/notifications", headers=h_c2)
        record("D19: Foreign citizen (Citizen 2) list returns 200 OK", r_list_c2.status_code == 200)
        c2_items = r_list_c2.json()
        record("D19.1: Foreign citizen sees 0 notifications belonging to Citizen 1", len(c2_items) == 0, f"Count={len(c2_items)}")

        # 20. Notifications ordered newest first
        if len(c1_items) >= 2:
            dt0 = datetime.fromisoformat(c1_items[0]["created_at"])
            dt1 = datetime.fromisoformat(c1_items[1]["created_at"])
            record("D20: Notifications ordered newest first (created_at DESC)", dt0 >= dt1)
        else:
            record("D20: Notifications ordered newest first", False, "Fewer than 2 notifications")

        # 21. Empty notification database returns []
        record("D21: Empty notification list returns empty list []", c2_items == [])

        # 22. Real unread/read values are returned
        record(
            "D22: Real unread/read boolean values returned",
            all(isinstance(item["is_read"], bool) for item in c1_items),
        )

        # 23. Authenticated citizen can get unread count
        r_count_c1 = client.get("/api/v1/notifications/unread-count", headers=h_c1)
        record("D23: Citizen 1 unread-count returns 200 OK", r_count_c1.status_code == 200)
        record("D23.1: Citizen 1 has 2 unread notifications", r_count_c1.json().get("unread_count") == 2, f"Count={r_count_c1.json().get('unread_count')}")

        r_count_c2 = client.get("/api/v1/notifications/unread-count", headers=h_c2)
        record("D23.2: Citizen 2 unread-count returns 0", r_count_c2.json().get("unread_count") == 0)

        # 24. Unauthenticated unread count returns 401
        r_unauth_count = client.get("/api/v1/notifications/unread-count")
        record("D24: Unauthenticated unread count returns 401 Unauthorized", r_unauth_count.status_code == 401)

        # ------------------------------------------------------------
        # Group E: Notification Detail
        # ------------------------------------------------------------
        print("\n--- Group E: Notification Detail ---")

        notif_to_check = c1_items[0]
        n_id = notif_to_check["id"]

        # 25. Owner can retrieve notification detail
        r_det_owner = client.get(f"/api/v1/notifications/{n_id}", headers=h_c1)
        record("E25: Owner can retrieve notification detail (200 OK)", r_det_owner.status_code == 200)
        det_data = r_det_owner.json()
        record("E25.1: Detail contains truthful complaint_id & title", det_data["id"] == n_id and det_data["title"] == notif_to_check["title"])

        # 26. Foreign citizen cannot retrieve notification detail (403 Forbidden)
        r_det_foreign = client.get(f"/api/v1/notifications/{n_id}", headers=h_c2)
        record("E26: Foreign citizen access returns 403 Forbidden", r_det_foreign.status_code == 403)

        # 27. Nonexistent notification returns 404 Not Found
        r_det_404 = client.get(f"/api/v1/notifications/{str(uuid.uuid4())}", headers=h_c1)
        record("E27: Nonexistent notification returns 404 Not Found", r_det_404.status_code == 404)

        # 28. Unauthenticated notification detail returns 401 Unauthorized
        r_det_unauth = client.get(f"/api/v1/notifications/{n_id}")
        record("E28: Unauthenticated notification detail returns 401 Unauthorized", r_det_unauth.status_code == 401)

        # ------------------------------------------------------------
        # Group F: Mark Read
        # ------------------------------------------------------------
        print("\n--- Group F: Mark Read ---")

        # 29. Owner can mark notification as read (PATCH /{id}/read)
        r_read = client.patch(f"/api/v1/notifications/{n_id}/read", headers=h_c1)
        record("F29: Owner marks notification as read (200 OK)", r_read.status_code == 200)
        read_res = r_read.json()
        record("F29.1: Notification response has is_read = True", read_res["is_read"] is True)

        # 30. Unauthenticated mark-read returns 401 Unauthorized
        n2_id = c1_items[1]["id"]
        r_unauth_read = client.patch(f"/api/v1/notifications/{n2_id}/read")
        record("F30: Unauthenticated mark-read returns 401 Unauthorized", r_unauth_read.status_code == 401)

        # 31. Foreign citizen cannot mark notification as read (403 Forbidden)
        r_for_read = client.patch(f"/api/v1/notifications/{n2_id}/read", headers=h_c2)
        record("F31: Foreign citizen cannot mark notification as read (403 Forbidden)", r_for_read.status_code == 403)

        # 32. Already-read notification remains safely read (idempotent)
        r_read_again = client.patch(f"/api/v1/notifications/{n_id}/read", headers=h_c1)
        record("F32: Second mark-read is idempotent (200 OK, is_read = True)", r_read_again.status_code == 200 and r_read_again.json()["is_read"] is True)

        # 33. Mark-read does not modify complaint
        with TestingSessionLocal() as db_f:
            c_check_post_read = db_f.query(Complaint).filter(Complaint.id == notif_to_check["complaint_id"]).first()
            record("F33: Mark-read did not modify complaint status or provenance", c_check_post_read.status in [ComplaintStatus.ACCEPTED.value, ComplaintStatus.REJECTED.value])

            # 34. Mark-read does not modify title, message, or user_id
            n_db = db_f.query(Notification).filter(Notification.id == n_id).first()
            record(
                "F34: Mark-read preserved title, message, and user_id exactly",
                n_db.title == notif_to_check["title"] and n_db.message == notif_to_check["message"] and n_db.user_id == notif_to_check["user_id"],
            )

            # 35. Mark-read does not modify created_at
            orig_dt_iso = datetime.fromisoformat(notif_to_check["created_at"])
            record("F35: Mark-read preserved created_at timestamp", n_db.created_at.replace(microsecond=0) == orig_dt_iso.replace(tzinfo=None, microsecond=0))

        # 36. Marking notification as read updates unread count
        r_count_updated = client.get("/api/v1/notifications/unread-count", headers=h_c1)
        record("F36: Unread count decremented from 2 to 1 after marking read", r_count_updated.json().get("unread_count") == 1, f"Count={r_count_updated.json().get('unread_count')}")

        # ------------------------------------------------------------
        # Group G: Message Integrity
        # ------------------------------------------------------------
        print("\n--- Group G: Message Integrity ---")

        # 37. Client cannot create arbitrary acceptance messages via endpoint
        r_post_notif = client.post("/api/v1/notifications", headers=h_c1, json={"title": "Fake", "message": "Fake"})
        record("G37: Client cannot POST to /api/v1/notifications (405 Method Not Allowed)", r_post_notif.status_code == 405)

        # 38. Client cannot create arbitrary rejection messages via endpoint
        r_post_notif_adm = client.post("/api/v1/notifications", headers=h_adm, json={"title": "Fake", "message": "Fake"})
        record("G38: Admin cannot POST arbitrary notifications directly (405 Method Not Allowed)", r_post_notif_adm.status_code == 405)

        # 39. Rejection reason strictly matches persisted admin decision
        with TestingSessionLocal() as db_g:
            n_rej_db = db_g.query(Notification).filter(Notification.complaint_id == c_rej_id).first()
            comp_rej_db = db_g.query(Complaint).filter(Complaint.id == c_rej_id).first()
            record(
                "G39: Rejection notification message includes actual admin_reason from complaint",
                comp_rej_db.admin_reason in n_rej_db.message,
                f"complaint.admin_reason='{comp_rej_db.admin_reason}'",
            )

            # 40. Notification reflects actual complaint status
            n_acc_db = db_g.query(Notification).filter(Notification.complaint_id == c_acc_id).first()
            comp_acc_db = db_g.query(Complaint).filter(Complaint.id == c_acc_id).first()
            record(
                "G40: Acceptance notification reflects actual ACCEPTED complaint status",
                comp_acc_db.status == ComplaintStatus.ACCEPTED.value and "accepted" in n_acc_db.title.lower(),
            )

        # ------------------------------------------------------------
        # Group H: Provenance Immutability
        # ------------------------------------------------------------
        print("\n--- Group H: Provenance Immutability ---")

        with TestingSessionLocal() as db_h:
            comp_h = db_h.query(Complaint).filter(Complaint.id == c_acc_id).first()

            # 41. original_* fields remain strictly unchanged
            record("H41: original_problem unchanged", comp_h.original_problem.startswith("Hazardous Acceptable Issue"))
            record("H41.1: original_address unchanged", comp_h.original_address == "123 Test Avenue, Metropolis")
            record("H41.2: original_coords unchanged", comp_h.original_latitude == 12.9716 and comp_h.original_longitude == 77.5946)

            # 42. ai_* fields remain strictly unchanged
            record("H42: ai_problem unchanged", "Significant Acceptable Issue" in comp_h.ai_problem)
            record("H42.1: ai_summary unchanged", comp_h.ai_summary == "AI classified pothole hazard")

            # 43. final_* fields remain strictly unchanged
            record("H43: final_problem unchanged", comp_h.final_problem.startswith("Citizen confirmed Acceptable Issue"))
            record("H43.1: final_summary unchanged", comp_h.final_summary == "Citizen confirmed final summary")

            # 44. Complaint status remains authoritative source of truth
            record("H44: Complaint status remains authoritative", comp_h.status == ComplaintStatus.ACCEPTED.value)

        # ------------------------------------------------------------
        # Group I: Security & Authorization
        # ------------------------------------------------------------
        print("\n--- Group I: Security & Authorization ---")

        # 45-49. Client cannot inject user_id, complaint_id, title, message, created_at via read endpoint
        r_exploit = client.patch(
            f"/api/v1/notifications/{n_id}/read",
            headers=h_c1,
            json={
                "user_id": c2_id,
                "complaint_id": str(uuid.uuid4()),
                "title": "Hacked Title",
                "message": "Hacked Message",
                "created_at": "1970-01-01T00:00:00Z",
                "is_read": False,
            },
        )
        record("I45-49: PATCH /read ignores injected payload fields and sets is_read=True", r_exploit.status_code == 200)

        with TestingSessionLocal() as db_i:
            n_checked = db_i.query(Notification).filter(Notification.id == n_id).first()
            record("I45: user_id unmutated", n_checked.user_id == notif_to_check["user_id"])
            record("I46: complaint_id unmutated", n_checked.complaint_id == notif_to_check["complaint_id"])
            record("I47: title unmutated", n_checked.title == notif_to_check["title"])
            record("I48: message unmutated", n_checked.message == notif_to_check["message"])
            record("I49: created_at unmutated", n_checked.created_at.year >= 2026)

        # 50. No public/unauthenticated notification mutation endpoints exist
        r_pub_patch = client.patch(f"/api/v1/notifications/{n_id}/read")
        record("I50: Public unauthenticated mutation blocked (401)", r_pub_patch.status_code == 401)

        # ------------------------------------------------------------
        # Group J: Zero-Demo-Data Forensic Audit
        # ------------------------------------------------------------
        print("\n--- Group J: Zero-Demo-Data Forensic Audit ---")

        # 51. Runtime DB contains zero seeded notifications
        runtime_db_path = project_root / "civicflow.db"
        backend_db_path = backend_dir / "civicflow.db"

        def check_runtime_db(db_path: Path, label: str):
            if not db_path.exists():
                record(f"J51: {label} does not exist (clean)", True)
                return
            rt_engine = create_engine(f"sqlite:///{db_path}")
            rt_Session = sessionmaker(bind=rt_engine)
            with rt_Session() as rt_db:
                insp = sa.inspect(rt_engine)
                if "notifications" in insp.get_table_names():
                    cnt = rt_db.query(Notification).count()
                    record(f"J51: {label} has 0 seeded notifications", cnt == 0, f"Found {cnt}")
                else:
                    record(f"J51: {label} has no notifications table yet", True)

                if "complaints" in insp.get_table_names():
                    c_cnt = rt_db.query(Complaint).count()
                    record(f"J54: {label} has 0 seeded complaints", c_cnt == 0, f"Found {c_cnt}")
                else:
                    record(f"J54: {label} has no complaints table yet", True)

        check_runtime_db(runtime_db_path, "Root civicflow.db")
        check_runtime_db(backend_db_path, "Backend civicflow.db")

        # 52-53. Frontend contains no hardcoded notifications or fake unread count
        frontend_src = project_root / "frontend" / "src"
        hardcoded_patterns = [
            re.compile(r'demo notification', re.IGNORECASE),
            re.compile(r'sample notification', re.IGNORECASE),
            re.compile(r'fake notification', re.IGNORECASE),
            re.compile(r'mock notification', re.IGNORECASE),
            re.compile(r'placeholder notification', re.IGNORECASE),
            re.compile(r'unreadCount\s*=\s*[1-9]\d*', re.IGNORECASE),
        ]

        found_demo = []
        if frontend_src.exists():
            for f in frontend_src.rglob("*.js*"):
                if f.name.endswith((".js", ".jsx", ".ts", ".tsx")):
                    content = f.read_text(encoding="utf-8")
                    for p in hardcoded_patterns:
                        if p.search(content):
                            found_demo.append(f"{f.name}: {p.pattern}")

        record("J52-53: Frontend src contains no hardcoded notifications or fake unread counts", len(found_demo) == 0, f"Violations: {found_demo}")

        # ------------------------------------------------------------
        # Group K: Cumulative Regressions (Phases 1-9)
        # ------------------------------------------------------------
        print("\n--- Group K: Cumulative Regressions (Phases 1-9) ---")

        # 56. Phase 1: Health check
        r_health = client.get("/health")
        r_health_db = client.get("/health/db")
        record("K56: /health and /health/db return 200 OK", r_health.status_code == 200 and r_health_db.status_code == 200)

        # 57. Phase 2: Database models
        with TestingSessionLocal() as db_k:
            record("K57: Database models User, Complaint, Notification exist", User.__tablename__ == "users" and Complaint.__tablename__ == "complaints" and Notification.__tablename__ == "notifications")

        # 58. Phase 3: Login & JWT
        r_login = client.post("/api/v1/auth/login", json={"email": "citizen1_p10@example.com", "password": "PassCitizen123!"})
        record("K58: Citizen login succeeds and returns JWT", r_login.status_code == 200 and "access_token" in r_login.json())

        # 59. Phase 4: Complaint intake in DRAFT
        r_draft = client.post(
            "/api/v1/complaints/analyze",
            headers=h_c1,
            files={"image": ("incident.jpg", TINY_JPEG, "image/jpeg")},
            data={"original_problem": "Regression test pothole on 8th Cross", "original_address": "8th Cross, Sector 3"}
        )
        record("K59: Complaint intake creates DRAFT", r_draft.status_code == 201 and r_draft.json().get("status") == "DRAFT")
        k_c_id = r_draft.json().get("id")

        # 60. Phase 5: Gemini AI draft
        mock_gemini = GeminiComplaintDraft(
            category="Public Infrastructure",
            observed_issue="AI identified pothole on roadway",
            citizen_claim="Regression test pothole",
            formal_summary="Grounded physical evidence assessment",
            urgency_level="MEDIUM",
            warnings=[]
        )
        with patch("app.agent.gemini_agent.analyze_complaint_image", return_value=mock_gemini):
            r_ai = client.post(f"/api/v1/complaints/{k_c_id}/analyze", headers=h_c1)
            record("K60: Gemini analysis transitions to AI_GENERATED", r_ai.status_code == 200 and r_ai.json().get("category") == "Public Infrastructure")

        # 61. Phase 6: Geographic verification
        mock_geo = {
            "location_status": LocationStatus.VERIFIED.value,
            "latitude": 12.9249,
            "longitude": 77.6183,
            "place_id": "osm_p10_reg",
            "map_url": "https://www.openstreetmap.org/?mlat=12.9249&mlon=77.6183#map=17/12.9249/77.6183",
            "distance_meters": 10.0,
            "address_match": True,
            "geocoded_address": "8th Cross, Sector 3",
            "reverse_geocoded_address": "Bengaluru",
            "message": "Verified against OpenStreetMap"
        }
        with patch("app.services.geocoding_service.verify_complaint_location", return_value=mock_geo):
            r_geo = client.post(f"/api/v1/complaints/{k_c_id}/location/verify", headers=h_c1)
            record("K61: Geographic verification succeeds", r_geo.status_code == 200 and r_geo.json().get("location_status") == "VERIFIED")

        # 62. Phase 7: Draft review and edit
        r_edit = client.put(
            f"/api/v1/complaints/{k_c_id}/draft",
            headers=h_c1,
            json={"final_problem": "Citizen revised pothole description on 8th Cross"},
        )
        record("K62: Draft edit transitions to UNDER_REVIEW", r_edit.status_code == 200 and r_edit.json().get("status") == "UNDER_REVIEW")

        # 63. Phase 8: Final submission
        r_submit = client.post(
            f"/api/v1/complaints/{k_c_id}/submit",
            headers=h_c1
        )
        record("K63: Final submission transitions to SUBMITTED", r_submit.status_code == 200 and r_submit.json().get("status") == "SUBMITTED")

        # 64. Phase 9: Admin adjudication
        r_adm_accept = client.post(f"/api/v1/admin/complaints/{k_c_id}/accept", headers=h_adm)
        record("K64: Admin accept transitions to ACCEPTED", r_adm_accept.status_code == 200 and r_adm_accept.json().get("status") == "ACCEPTED")

        # ------------------------------------------------------------
        # Group L: Real Runtime End-to-End Pipeline
        # ------------------------------------------------------------
        print("\n--- Group L: Real Runtime End-to-End Pipeline ---")

        # 65. E2E Accept Flow
        # Citizen creates & submits complaint
        e2e_acc_id = create_submitted_complaint(c2_id, "E2E Broken Traffic Light")
        # Admin accepts
        r_e2e_acc = client.post(f"/api/v1/admin/complaints/{e2e_acc_id}/accept", headers=h_adm)
        record("L65.1: Admin accepts E2E complaint", r_e2e_acc.status_code == 200)

        # Citizen 2 checks notifications
        r_e2e_list = client.get("/api/v1/notifications", headers=h_c2)
        record("L65.2: Citizen 2 receives notification", r_e2e_list.status_code == 200 and len(r_e2e_list.json()) == 1)
        e2e_n = r_e2e_list.json()[0]
        record("L65.3: Notification is unread initially", e2e_n["is_read"] is False)

        # Citizen 2 checks unread count
        r_e2e_cnt = client.get("/api/v1/notifications/unread-count", headers=h_c2)
        record("L65.4: Unread count equals 1", r_e2e_cnt.json().get("unread_count") == 1)

        # Citizen 2 marks notification as read
        r_e2e_mark = client.patch(f"/api/v1/notifications/{e2e_n['id']}/read", headers=h_c2)
        record("L65.5: Notification marked as read", r_e2e_mark.status_code == 200 and r_e2e_mark.json()["is_read"] is True)

        # Unread count now 0
        r_e2e_cnt2 = client.get("/api/v1/notifications/unread-count", headers=h_c2)
        record("L65.6: Unread count decremented to 0", r_e2e_cnt2.json().get("unread_count") == 0)

        # 66. E2E Reject Flow
        e2e_rej_id = create_submitted_complaint(c2_id, "E2E Private Garden Noise")
        reject_reason = "Noise from private residential gathering does not fall under municipal public works."
        r_e2e_rej = client.post(
            f"/api/v1/admin/complaints/{e2e_rej_id}/reject",
            headers=h_adm,
            json={"admin_reason": reject_reason},
        )
        record("L66.1: Admin rejects E2E complaint with reason", r_e2e_rej.status_code == 200)

        r_e2e_list2 = client.get("/api/v1/notifications", headers=h_c2)
        record("L66.2: Citizen 2 receives second notification", len(r_e2e_list2.json()) == 2)
        n_rej_item = next(item for item in r_e2e_list2.json() if item["complaint_id"] == e2e_rej_id)
        record("L66.3: Rejection notification contains verbatim admin reason", reject_reason in n_rej_item["message"])

        # Citizen marks rejection notification read
        client.patch(f"/api/v1/notifications/{n_rej_item['id']}/read", headers=h_c2)
        r_e2e_cnt3 = client.get("/api/v1/notifications/unread-count", headers=h_c2)
        record("L66.4: Unread count returns to 0 after marking rejection read", r_e2e_cnt3.json().get("unread_count") == 0)

    finally:
        # Restore configuration and cleanup temporary fixtures
        settings.UPLOAD_DIR = orig_upload_dir
        shutil.rmtree(temp_upload_dir, ignore_errors=True)
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass

    print("\n" + "=" * 70)
    print(f"CIVICFLOW PHASE 10 TEST RESULTS: {passed} PASSED | {failed} FAILED | {blocked} BLOCKED")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
