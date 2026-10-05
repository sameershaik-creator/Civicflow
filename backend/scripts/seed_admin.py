"""
=============================================================================
CivicFlow — Development & Testing Admin Seeder
=============================================================================
DEVELOPMENT AND TESTING SEED SCRIPT ONLY — NEVER RUN IN PRODUCTION.

Public registration in CivicFlow cannot and will never create admin users.
This script provides an out-of-band administrative seeding mechanism for
local development and integration testing.

Usage:
    python backend/scripts/seed_admin.py --name "Admin Name" --email "admin@example.com" --password "SecurePassword123"

Or via environment variables:
    SEED_ADMIN_NAME="Municipal Admin"
    SEED_ADMIN_EMAIL="admin@civicflow.org"
    SEED_ADMIN_PASSWORD="StrongDevPassword456!"
    python backend/scripts/seed_admin.py
"""

import sys
import os
import argparse
from pathlib import Path

# Resolve paths
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.services import auth_service
from app.models.user import UserRole


def seed_admin(name: str, email: str, password: str):
    db = SessionLocal()
    try:
        print(f"[*] Checking if admin user '{email}' already exists...")
        existing = auth_service.get_user_by_email(db, email)
        if existing:
            print(f"[!] User with email '{email}' already exists (role={existing.role}).")
            if existing.role != UserRole.ADMIN.value:
                print(f"[*] Elevating existing user to admin role...")
                existing.role = UserRole.ADMIN.value
                db.commit()
                print(f"[+] User '{email}' role updated to '{UserRole.ADMIN.value}'.")
            else:
                print(f"[+] User is already an administrator.")
            return existing

        print(f"[*] Seeding new administrator account for '{email}'...")
        admin_user = auth_service.create_admin_user(
            db=db,
            name=name,
            email=email,
            password=password
        )
        print(f"[+] Admin successfully created with ID: {admin_user.id}")
        print(f"[+] Role: {admin_user.role}")
        return admin_user
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed an administrator user for CivicFlow (Dev/Test only).")
    parser.add_argument("--name", default=os.getenv("SEED_ADMIN_NAME", "Civic Administrator"), help="Admin full name")
    parser.add_argument("--email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@civicflow.org"), help="Admin email address")
    parser.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD", "AdminPass123!"), help="Admin password")

    args = parser.parse_args()

    if not args.password:
        print("[ERROR] Password must be supplied via --password or SEED_ADMIN_PASSWORD env var.")
        sys.exit(1)

    seed_admin(name=args.name, email=args.email, password=args.password)


if __name__ == "__main__":
    main()
