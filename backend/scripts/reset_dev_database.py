"""
CivicFlow — Development & Hackathon Database Reset Script
Resets the local development SQLite database to a completely clean state:
- Deletes all records from notifications, complaints, users.
- Preserves database schema, tables, indexes, and alembic_version.
- Removes old test assets from uploads/complaints/.
- Seeds the legitimate administrator account (admin@civicflow.org / AdminPass123!).
"""

import sys
import os
from pathlib import Path

# Resolve paths
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import SessionLocal, engine, text
from app.models.user import User, UserRole
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.services import auth_service, media_service


def reset_dev_database():
    db_url = str(settings.DATABASE_URL)
    print(f"[*] Checking database target: {db_url}")

    # Safety check: strictly restrict to local SQLite dev database
    if not (db_url.startswith("sqlite") or "civicflow.db" in db_url):
        print(f"[ERROR] Refusing to reset non-development database: {db_url}")
        sys.exit(1)

    print("[*] Verified development database target. Proceeding with clean reset...")

    db = SessionLocal()
    try:
        # 1. Atomic deletion of test records
        deleted_notifs = db.query(Notification).delete()
        deleted_complaints = db.query(Complaint).delete()
        deleted_users = db.query(User).delete()
        db.commit()
        print(f"[+] Cleared database records: {deleted_notifs} notifications, {deleted_complaints} complaints, {deleted_users} users.")

        # 2. Clean up test uploaded assets in uploads/complaints/
        uploads_dir = media_service.get_upload_directory()
        deleted_files = 0
        if uploads_dir.exists():
            for f in uploads_dir.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    try:
                        f.unlink()
                        deleted_files += 1
                    except Exception as err:
                        print(f"[!] Warning: Could not delete {f.name}: {err}")
        print(f"[+] Cleared {deleted_files} physical evidence files from {uploads_dir}.")

        # 3. Seed legitimate administrator account
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@civicflow.org")
        admin_pass = os.getenv("SEED_ADMIN_PASSWORD", "AdminPass123!")
        admin_name = os.getenv("SEED_ADMIN_NAME", "Civic Administrator")

        admin_user = auth_service.create_admin_user(
            db=db,
            name=admin_name,
            email=admin_email,
            password=admin_pass
        )
        print(f"[+] Seeded legitimate administrator: {admin_user.email} (Role: {admin_user.role}, ID: {admin_user.id})")

        # 4. Verification of fresh state
        total_users = db.query(User).count()
        total_admins = db.query(User).filter(User.role == UserRole.ADMIN.value).count()
        total_citizens = db.query(User).filter(User.role == UserRole.CITIZEN.value).count()
        total_complaints = db.query(Complaint).count()
        total_notifications = db.query(Notification).count()

        print("========================================")
        print("   FRESH HACKATHON STATE VERIFICATION   ")
        print("========================================")
        print(f"Total Users: {total_users} (Admins: {total_admins}, Citizens: {total_citizens})")
        print(f"Total Complaints: {total_complaints}")
        print(f"Total Notifications: {total_notifications}")
        print(f"Admin Credentials: {admin_email} / {admin_pass}")
        print("Status: FRESH & READY")
        print("========================================")

        assert total_complaints == 0, "Complaints must be 0"
        assert total_notifications == 0, "Notifications must be 0"
        assert total_citizens == 0, "Citizens must be 0"
        assert total_admins == 1, "Exactly 1 admin must exist"

        return True
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database reset failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_dev_database()
