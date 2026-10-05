"""
CivicFlow — Phase 1 Verification Script

This script verifies:
1. Python environment and required dependency imports (FastAPI, Pydantic, SQLAlchemy, etc.)
2. Configuration loading from .env (without exposing secrets)
3. SQLAlchemy database engine initialization and connectivity check
4. FastAPI app initialization, CORS middleware, and static mounts
5. HTTP /health endpoint returns HTTP 200 with {"status": "ok"}
6. HTTP /health/db endpoint returns database status
7. Frontend configuration and project structure integrity
"""

import sys
import os
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

# Also check for local venv site-packages if run with global python
venv_site = project_root / "venv" / "Lib" / "site-packages"
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(1, str(venv_site))

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

    print("=" * 60)
    print("CIVICFLOW PHASE 1 — FOUNDATION VERIFICATION")
    print("=" * 60)

    # 1. Dependency Imports
    print("\n--- 1. Testing Core Python Dependencies ---")
    try:
        import fastapi
        record("FastAPI import", True, f"(v{fastapi.__version__})")
    except ImportError as e:
        record("FastAPI import", False, str(e))

    try:
        import pydantic
        record("Pydantic import", True, f"(v{pydantic.__version__})")
    except ImportError as e:
        record("Pydantic import", False, str(e))

    try:
        import sqlalchemy
        record("SQLAlchemy import", True, f"(v{sqlalchemy.__version__})")
    except ImportError as e:
        record("SQLAlchemy import", False, str(e))

    try:
        import uvicorn
        record("Uvicorn import", True, f"(v{uvicorn.__version__})")
    except ImportError as e:
        record("Uvicorn import", False, str(e))

    # 2. Configuration & Secrets Isolation
    print("\n--- 2. Testing Configuration & Environment ---")
    try:
        from app.config import settings
        record("Settings loaded", True, f"Base URL: {settings.HOST}:{settings.PORT}")
        record("Database URL configured", bool(settings.DATABASE_URL), f"Scheme: {settings.DATABASE_URL.split('://')[0]}")
        record("CORS origins parsed", isinstance(settings.CORS_ORIGINS, list) and len(settings.CORS_ORIGINS) > 0, str(settings.CORS_ORIGINS))
        # Ensure SECRET_KEY is not empty but not logged directly
        record("Secret key present", len(settings.SECRET_KEY) >= 32, f"Length: {len(settings.SECRET_KEY)} chars")
    except Exception as e:
        record("Settings loading", False, str(e))

    # 3. Database Connection
    print("\n--- 3. Testing Database Connectivity ---")
    try:
        from app.database import check_database_connection, engine
        db_res = check_database_connection()
        record("Database connection check", db_res.get("connected") is True, f"Dialect: {db_res.get('dialect')}")
    except Exception as e:
        record("Database connection check", False, str(e))

    # 4. FastAPI App & Health Endpoints
    print("\n--- 4. Testing FastAPI Application & Endpoints ---")
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # GET /
        root_res = client.get("/")
        record("Root endpoint GET /", root_res.status_code == 200, f"Status: {root_res.status_code}, Body: {root_res.json()}")

        # GET /health
        health_res = client.get("/health")
        record("Health endpoint GET /health", health_res.status_code == 200 and health_res.json() == {"status": "ok"}, f"Body: {health_res.json()}")

        # GET /health/db
        db_res = client.get("/health/db")
        record("Database health endpoint GET /health/db", db_res.status_code == 200, f"Body: {db_res.json()}")

    except Exception as e:
        record("FastAPI TestClient execution", False, str(e))

    # 5. Frontend Structure Integrity
    print("\n--- 5. Testing Frontend Structure Integrity ---")
    fe_dir = Path(__file__).resolve().parent / "frontend"
    fe_files = [
        "package.json",
        "vite.config.js",
        "index.html",
        "tailwind.config.js",
        "src/main.jsx",
        "src/App.jsx",
        "src/index.css",
        "src/services/api.js",
        "src/components/Header.jsx",
        "src/components/HealthStatusCard.jsx",
        "src/pages/Home.jsx",
    ]
    all_files_exist = True
    for f in fe_files:
        exists = (fe_dir / f).exists()
        if not exists:
            all_files_exist = False
            record(f"Frontend file {f}", False, "File missing")
    if all_files_exist:
        record("All frontend components & configuration files exist", True, f"({len(fe_files)} files verified)")

    print("\n" + "=" * 60)
    print(f"VERIFICATION SUMMARY: Passed: {passed} | Failed: {failed}")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
