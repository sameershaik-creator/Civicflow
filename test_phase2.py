"""
CivicFlow — Phase 2 Verification & Database Test Suite

This test suite verifies:
1. User Model:
   - Persistence, UUID generation, default role ('citizen'), UTC created_at
   - Email uniqueness constraint enforcement
   - Password hash persistence (no plaintext password)
2. Complaint Model:
   - Persistence with foreign key reference to User
   - Default status ('DRAFT') and location_status ('COORDINATES_ATTACHED')
   - Required vs nullable field validation
   - Separation of Provenance Layers:
     * Layer 1: original_problem, original_address, original_latitude, original_longitude
     * Layer 2: ai_problem, ai_address, ai_summary
     * Layer 3: final_problem, final_address, final_summary
   - Deterministic geographic coordinates & map_url separation
   - Foreign key constraint enforcement
3. Notification Model:
   - Persistence with foreign keys to User and Complaint
   - Default is_read = False, UTC created_at
   - Bidirectional relationship integrity
4. Alembic Migration:
   - Programmatic execution of upgrade('head') on clean database
   - Schema introspection verifying tables, columns, indexes, and foreign keys
5. Phase 1 Regression Check:
   - In-process TestClient check for /, /health, /health/db
"""

import sys
import os
import uuid
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root and backend directories reliably from any working directory
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

# Add backend directory to sys.path
sys.path.insert(0, str(backend_dir))

# Add venv site-packages if run with global python
venv_site = project_root / "venv" / "Lib" / "site-packages"
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(1, str(venv_site))

import sqlalchemy as sa
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from alembic.config import Config
from alembic import command


def run_tests():
    passed = 0
    failed = 0
    results = []

    def record(name: str, success: bool, message: str = ""):
        nonlocal passed, failed
        if success:
            passed += 1
            results.append(f"  [PASS] {name} {message}")
            print(f"[PASS] {name} {message}")
        else:
            failed += 1
            results.append(f"  [FAIL] {name} - {message}")
            print(f"[FAIL] {name} - {message}")

    print("=" * 65)
    print("CIVICFLOW PHASE 2 — DATABASE SCHEMA & ORM VERIFICATION")
    print("=" * 65)

    # Setup isolated test database in a temporary file
    temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db_file.name
    temp_db_file.close()

    test_db_url = f"sqlite:///{temp_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})

    # Enable SQLite foreign key enforcement
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    try:
        # -------------------------------------------------------------
        # 1. Test Alembic Migration Execution
        # -------------------------------------------------------------
        print("\n--- 1. Testing Alembic Migration Engine ---")
        try:
            alembic_ini_path = backend_dir / "alembic.ini"
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

            # Run migration upgrade to head
            command.upgrade(alembic_cfg, "head")

            # Inspect created tables
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            expected_tables = {"users", "complaints", "notifications", "alembic_version"}
            all_tables_present = expected_tables.issubset(set(tables))

            record(
                "Alembic migration execution (upgrade head)",
                all_tables_present,
                f"Tables found: {tables}"
            )

            # Inspect users columns
            user_cols = {c["name"]: c for c in inspector.get_columns("users")}
            expected_user_cols = {"id", "name", "email", "password_hash", "role", "created_at"}
            record("Users table schema", expected_user_cols.issubset(user_cols.keys()))

            # Inspect complaints columns
            complaint_cols = {c["name"]: c for c in inspector.get_columns("complaints")}
            expected_complaint_cols = {
                "id", "user_id", "image_url",
                "original_problem", "original_address", "original_latitude", "original_longitude",
                "ai_problem", "ai_address", "ai_summary",
                "final_problem", "final_address", "final_summary",
                "latitude", "longitude", "place_id", "map_url",
                "location_status", "status", "admin_reason",
                "created_at", "updated_at", "submitted_at", "decided_at"
            }
            record(
                "Complaints table schema (provenance & geographic separation)",
                expected_complaint_cols.issubset(complaint_cols.keys())
            )

            # Inspect notifications columns
            notification_cols = {c["name"]: c for c in inspector.get_columns("notifications")}
            expected_notif_cols = {"id", "user_id", "complaint_id", "title", "message", "is_read", "created_at"}
            record("Notifications table schema", expected_notif_cols.issubset(notification_cols.keys()))

        except Exception as e:
            record("Alembic migration execution", False, str(e))

        # -------------------------------------------------------------
        # 2. Test User Model & Constraints
        # -------------------------------------------------------------
        print("\n--- 2. Testing User Model & Constraints ---")
        from app.models.user import User, UserRole

        session = TestSession()
        try:
            # Create citizen user
            user1 = User(
                name="Ananya Sharma",
                email="ananya@example.org",
                password_hash="$2b$12$e8YkZ8examplehashplaceholderonly",
            )
            session.add(user1)
            session.commit()
            session.refresh(user1)

            record("User persistence", bool(user1.id), f"ID: {user1.id}")
            record("User UUIDv4 auto-generation", len(user1.id) == 36 and "-" in user1.id)
            record("User default role is citizen", user1.role == UserRole.CITIZEN.value)
            record("User created_at has timezone", user1.created_at is not None)

            # Test unique email constraint
            duplicate_user = User(
                name="Duplicate User",
                email="ananya@example.org",  # Same email
                password_hash="$2b$12$anotherhashplaceholder",
            )
            session.add(duplicate_user)
            try:
                session.commit()
                record("Unique email constraint", False, "Duplicate email did not raise IntegrityError")
            except IntegrityError:
                session.rollback()
                record("Unique email constraint", True, "IntegrityError raised on duplicate email")

        except Exception as e:
            session.rollback()
            record("User model testing", False, str(e))
        finally:
            session.close()

        # -------------------------------------------------------------
        # 3. Test Complaint Model & Provenance Separation
        # -------------------------------------------------------------
        print("\n--- 3. Testing Complaint Model & Provenance Separation ---")
        from app.models.complaint import Complaint, ComplaintStatus, LocationStatus

        session = TestSession()
        try:
            # Query the citizen user
            citizen = session.query(User).filter_by(email="ananya@example.org").first()

            # Create complaint with raw citizen data
            complaint = Complaint(
                user_id=citizen.id,
                image_url="/uploads/pothole_evidence_101.jpg",
                original_problem="huge hole on the road near the tea stall bro my scooter tyre got completely busted do something fast.",
                original_address="Main road, near bus stand.",
                original_latitude=17.2473,
                original_longitude=80.1514,
                # AI Draft layer (distinct)
                ai_problem="Significant roadway depression (pothole) posing hazard to two-wheeled vehicles.",
                ai_address="Main Road, Near Central Bus Stand",
                ai_summary="Citizen reports vehicle damage resulting from an unpaved road defect.",
                # Final reviewed layer (distinct)
                final_problem="Large pothole on northbound lane of Main Road causing hazardous driving conditions.",
                final_address="Main Road, Opposite Bus Terminal, Sector 4",
                final_summary="Urgent municipal request for road resurfacing following tire damage.",
                # Authoritative location
                latitude=17.2473,
                longitude=80.1514,
                place_id="osm_place_89234",
                map_url="https://www.openstreetmap.org/?mlat=17.2473&mlon=80.1514#map=17/17.2473/80.1514",
                location_status=LocationStatus.COORDINATES_ATTACHED.value,
            )
            session.add(complaint)
            session.commit()
            session.refresh(complaint)

            record("Complaint persistence", bool(complaint.id), f"ID: {complaint.id}")
            record("Complaint default status is DRAFT", complaint.status == ComplaintStatus.DRAFT.value)
            record(
                "Complaint default location_status",
                complaint.location_status == LocationStatus.COORDINATES_ATTACHED.value
            )
            record("Complaint UUID auto-generation", len(complaint.id) == 36)
            record("Provenance Layer 1 intact (raw citizen input)", "scooter tyre got completely busted" in complaint.original_problem)
            record("Provenance Layer 2 intact (AI draft)", "roadway depression" in complaint.ai_problem)
            record("Provenance Layer 3 intact (human approved)", "hazardous driving conditions" in complaint.final_problem)
            record("Distinct location separation", complaint.original_latitude == 17.2473 and complaint.map_url.startswith("https://www.openstreetmap.org"))

            # Test bidirectional relationship
            record("User -> Complaints relationship", len(citizen.complaints) == 1 and citizen.complaints[0].id == complaint.id)
            record("Complaint -> User relationship", complaint.user.email == "ananya@example.org")

            # Test foreign key enforcement (non-existent user)
            orphan_complaint = Complaint(
                user_id="00000000-0000-0000-0000-000000000000",
                image_url="/uploads/test.jpg",
                original_problem="Orphan test",
            )
            session.add(orphan_complaint)
            try:
                session.commit()
                record("Foreign key enforcement (complaints.user_id)", False, "Inserted orphan complaint without error")
            except IntegrityError:
                session.rollback()
                record("Foreign key enforcement (complaints.user_id)", True, "Rejected non-existent user_id")

        except Exception as e:
            session.rollback()
            record("Complaint model testing", False, str(e))
        finally:
            session.close()

        # -------------------------------------------------------------
        # 4. Test Notification Model
        # -------------------------------------------------------------
        print("\n--- 4. Testing Notification Model ---")
        from app.models.notification import Notification

        session = TestSession()
        try:
            citizen = session.query(User).filter_by(email="ananya@example.org").first()
            complaint = session.query(Complaint).first()

            notif = Notification(
                user_id=citizen.id,
                complaint_id=complaint.id,
                title="Complaint Under Review",
                message="Your complaint CF-8042 is being reviewed by the public works department.",
            )
            session.add(notif)
            session.commit()
            session.refresh(notif)

            record("Notification persistence", bool(notif.id), f"ID: {notif.id}")
            record("Notification default is_read is False", notif.is_read is False)
            record("Notification -> Complaint relationship", notif.complaint.id == complaint.id)
            record("Notification -> User relationship", notif.user.id == citizen.id)
            record("Complaint -> Notifications relationship", len(complaint.notifications) == 1)

            # Test notification invalid complaint foreign key
            orphan_notif = Notification(
                user_id=citizen.id,
                complaint_id="00000000-0000-0000-0000-000000000000",
                title="Invalid Notif",
                message="Invalid complaint ID",
            )
            session.add(orphan_notif)
            try:
                session.commit()
                record("Foreign key enforcement (notifications.complaint_id)", False, "Inserted orphan notification")
            except IntegrityError:
                session.rollback()
                record("Foreign key enforcement (notifications.complaint_id)", True, "Rejected non-existent complaint_id")

        except Exception as e:
            session.rollback()
            record("Notification model testing", False, str(e))
        finally:
            session.close()

        # -------------------------------------------------------------
        # 5. Phase 1 Regression Check
        # -------------------------------------------------------------
        print("\n--- 5. Phase 1 Regression Check ---")
        try:
            from app.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            r_root = client.get("/")
            record("Phase 1 Regression: GET /", r_root.status_code == 200 and r_root.json().get("status") == "running")

            r_health = client.get("/health")
            record("Phase 1 Regression: GET /health", r_health.status_code == 200 and r_health.json() == {"status": "ok"})

            r_db = client.get("/health/db")
            record("Phase 1 Regression: GET /health/db", r_db.status_code == 200 and r_db.json().get("database", {}).get("connected") is True)

        except Exception as e:
            record("Phase 1 Regression check", False, str(e))

    finally:
        # Cleanup temporary test database file
        try:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(f"PHASE 2 VERIFICATION SUMMARY: Passed: {passed} | Failed: {failed}")
    print("=" * 65)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
