import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import check_database_connection
import app.models  # Registers ORM models with Base.metadata
from app.api.auth import router as auth_router
from app.api.complaints import router as complaints_router
from app.api.admin import router as admin_router
from app.api.notifications import router as notifications_router

is_production = getattr(settings, "ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title="CivicFlow API",
    description="Civic complaint intake, AI drafting, and municipal adjudication platform.",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists (media is served exclusively via authorized API routes)
upload_path = Path(__file__).resolve().parent.parent / settings.UPLOAD_DIR
upload_path.mkdir(parents=True, exist_ok=True)

# Include Routers
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(complaints_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")

# Core endpoints
@app.get("/")
def read_root():
    return {
        "name": "CivicFlow API",
        "description": "Civic issue reporting made clearer.",
        "version": "0.1.0",
        "status": "running"
    }


def check_debug_access():
    """Guards development-only diagnostic and maintenance endpoints from public exposure in production."""
    if is_production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )


@app.get("/healthz", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    """Real backend health check and liveness probe returning HTTP 200 with status ok."""
    return {"status": "ok"}


@app.get("/readyz", tags=["Health"])
@app.get("/health/db", tags=["Health"])
def health_db_check():
    """Database connectivity test probe and readiness probe."""
    db_status = check_database_connection()
    if not db_status.get("connected"):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": db_status}
        )
    return {
        "status": "ok",
        "database": db_status
    }


@app.api_route("/api/v1/maintenance/reset-dev-data", methods=["GET", "POST"])
def trigger_reset_dev_data():
    check_debug_access()
    from scripts.reset_dev_database import reset_dev_database
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    from app.models.complaint import Complaint
    from app.models.notification import Notification

    success = reset_dev_database()
    db = SessionLocal()
    try:
        users_count = db.query(User).count()
        admins_count = db.query(User).filter(User.role == UserRole.ADMIN.value).count()
        complaints_count = db.query(Complaint).count()
        notifications_count = db.query(Notification).count()
        return {
            "status": "success",
            "message": "Development database reset successfully to clean state.",
            "users": users_count,
            "admins": admins_count,
            "complaints": complaints_count,
            "notifications": notifications_count
        }
    finally:
        db.close()


@app.get("/api/v1/debug/complaints-all")
def debug_all_complaints():
    check_debug_access()
    from app.database import SessionLocal
    from app.models.complaint import Complaint
    db = SessionLocal()
    try:
        complaints = db.query(Complaint).all()
        return [
            {
                "id": c.id,
                "user_id": c.user_id,
                "original_problem": c.original_problem,
                "original_address": c.original_address,
                "original_latitude": c.original_latitude,
                "original_longitude": c.original_longitude,
                "ai_problem": c.ai_problem,
                "ai_address": c.ai_address,
                "ai_summary": c.ai_summary,
                "final_problem": c.final_problem,
                "final_address": c.final_address,
                "final_summary": c.final_summary,
                "location_status": c.location_status,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                "decided_at": c.decided_at.isoformat() if c.decided_at else None,
            }
            for c in complaints
        ]
    finally:
        db.close()


@app.get("/api/v1/debug/users-all")
def debug_all_users():
    check_debug_access()
    from app.database import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    finally:
        db.close()


@app.get("/api/v1/debug/complaint-response/{complaint_id}")
def debug_serialized_complaint(complaint_id: str):
    check_debug_access()
    from app.database import SessionLocal
    from app.models.complaint import Complaint
    from app.schemas.complaint import ComplaintResponse
    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
        if not complaint:
            return {"error": "not found"}
        return ComplaintResponse.model_validate(complaint).model_dump(mode="json")
    finally:
        db.close()


@app.get("/api/v1/debug/gemini-quota")
def debug_gemini_quota():
    check_debug_access()
    """Checks the actual configured Gemini model, google-genai version, and live API quota status."""
    import time
    from app.config import settings

    configured_model = (settings.GEMINI_MODEL or "gemini-3.1-flash-lite").strip()
    api_key_present = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    genai_version = "unknown"
    try:
        import google.genai as genai
        genai_version = getattr(genai, "__version__", "unknown")
    except Exception as e:
        genai_version = f"import_error: {e}"

    if not api_key_present:
        return {
            "configured_model": configured_model,
            "google_genai_version": genai_version,
            "api_key_configured": False,
            "quota_exhausted": "UNKNOWN",
            "error": "GEMINI_API_KEY is not configured"
        }

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())

        # List available models
        available_models = []
        try:
            for m in client.models.list():
                m_name = getattr(m, "name", "")
                if "gemini" in m_name.lower():
                    available_models.append(m_name)
        except Exception as le:
            available_models = [f"list_error: {le}"]

        # Test gemini-3.5-flash-lite with multimodal image and Pydantic structured output
        full_error = None
        try:
            from app.schemas.ai import GeminiComplaintDraft
            tiny_jpeg = (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
                b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
                b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
                b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
                b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
                b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
            )
            image_part = types.Part.from_bytes(data=tiny_jpeg, mime_type="image/jpeg")
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiComplaintDraft,
                temperature=0.1,
                max_output_tokens=300
            )
            t0 = time.perf_counter()
            resp = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[image_part, "Analyze this image for civic issue triage. Citizen problem: Broken curb on corner."],
                config=config
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0

            parsed_data = None
            if hasattr(resp, "parsed") and resp.parsed:
                if isinstance(resp.parsed, GeminiComplaintDraft):
                    parsed_data = resp.parsed.model_dump()
                elif isinstance(resp.parsed, dict):
                    parsed_data = GeminiComplaintDraft.model_validate(resp.parsed).model_dump()
            elif hasattr(resp, "text") and resp.text:
                import json
                cleaned = resp.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed_data = GeminiComplaintDraft.model_validate_json(cleaned).model_dump()

            return {
                "configured_model": configured_model,
                "tested_model": "gemini-3.5-flash-lite",
                "google_genai_version": genai_version,
                "api_key_configured": True,
                "quota_exhausted": "NO",
                "multimodal_supported": True,
                "structured_output_supported": bool(parsed_data),
                "latency_ms": round(latency_ms, 2),
                "parsed_sample": parsed_data,
                "status": "operational"
            }
        except Exception as e:
            full_error = {
                "exception_type": type(e).__name__,
                "args": [str(a) for a in getattr(e, "args", [])],
                "code": getattr(e, "code", None),
                "message": getattr(e, "message", str(e)),
                "details": getattr(e, "details", None)
            }
            err_str = str(e)
            is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

        return {
            "configured_model": configured_model,
            "tested_model": "gemini-3.5-flash-lite",
            "google_genai_version": genai_version,
            "api_key_configured": True,
            "quota_exhausted": "YES" if is_429 else "UNKNOWN",
            "full_error": full_error
        }
    except Exception as e:
        err_str = str(e)
        is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
        return {
            "configured_model": configured_model,
            "google_genai_version": genai_version,
            "api_key_configured": True,
            "quota_exhausted": "YES" if is_429 else "UNKNOWN",
            "error_type": type(e).__name__,
            "error_details": err_str,
            "status": "exhausted" if is_429 else "error"
        }


@app.get("/api/v1/debug/anti-hardcode-test")
def debug_anti_hardcode_test():
    check_debug_access()
    """
    Executes live verification with TWO genuinely different real complaints
    against the configured real Gemini API (Section 18).
    Proves outputs are dynamic, non-canned, and specific to each incident evidence.
    """
    from app.agent import gemini_agent
    from pathlib import Path
    import time

    upload_dir = Path(__file__).resolve().parent.parent / "uploads" / "complaints"
    img_a_path = upload_dir / "803038e39cd84f87bcc3c36f63cc7605.jpg"
    img_b_path = upload_dir / "1160120e58bd43a58fa4fe4e348d57d4.jpg"

    if not img_a_path.exists() or not img_b_path.exists():
        return {"error": "Test images not found in uploads/complaints"}

    bytes_a = img_a_path.read_bytes()
    bytes_b = img_b_path.read_bytes()

    # Complaint A: Real Pothole
    t0_a = time.perf_counter()
    draft_a, timing_a = gemini_agent.analyze_complaint_image(
        image_bytes=bytes_a,
        mime_type="image/jpeg",
        citizen_problem="Large deep road crater pothole near intersection posing vehicle damage risk",
        address="Near Main University Gate Road",
        latitude=16.742407,
        longitude=74.384201,
        return_latency=True
    )
    total_a_ms = (time.perf_counter() - t0_a) * 1000.0

    # Complaint B: Real University Entrance Gate (Streetlight Request)
    t0_b = time.perf_counter()
    draft_b, timing_b = gemini_agent.analyze_complaint_image(
        image_bytes=bytes_b,
        mime_type="image/jpeg",
        citizen_problem="Requesting high-mast street illumination outside campus arch gate",
        address="Entrance Gate, Sanjay Ghodawat University",
        latitude=16.742373,
        longitude=74.384135,
        return_latency=True
    )
    total_b_ms = (time.perf_counter() - t0_b) * 1000.0

    is_distinct = (
        draft_a.observed_issue != draft_b.observed_issue and
        draft_a.formal_summary != draft_b.formal_summary
    )

    return {
        "configured_model": settings.GEMINI_MODEL,
        "anti_hardcode_verified": is_distinct,
        "complaint_a": {
            "evidence_image_bytes": len(bytes_a),
            "input_problem": "Large deep road crater pothole near intersection posing vehicle damage risk",
            "category": draft_a.category,
            "urgency_level": draft_a.urgency_level,
            "observed_issue": draft_a.observed_issue,
            "citizen_claim": draft_a.citizen_claim,
            "formal_summary": draft_a.formal_summary,
            "warnings": draft_a.warnings,
            "gemini_latency_ms": timing_a["t3_to_t4_gemini_ms"],
            "pydantic_latency_ms": timing_a["t4_to_t5_pydantic_ms"],
            "total_ms": round(total_a_ms, 2)
        },
        "complaint_b": {
            "evidence_image_bytes": len(bytes_b),
            "input_problem": "Requesting high-mast street illumination outside campus arch gate",
            "category": draft_b.category,
            "urgency_level": draft_b.urgency_level,
            "observed_issue": draft_b.observed_issue,
            "citizen_claim": draft_b.citizen_claim,
            "formal_summary": draft_b.formal_summary,
            "warnings": draft_b.warnings,
            "gemini_latency_ms": timing_b["t3_to_t4_gemini_ms"],
            "pydantic_latency_ms": timing_b["t4_to_t5_pydantic_ms"],
            "total_ms": round(total_b_ms, 2)
        }
    }


@app.get("/api/v1/debug/verify-gemini-31")
def debug_verify_gemini_31():
    check_debug_access()
    """
    Dedicated test suite for gemini-3.1-flash-lite:
    1. Single minimal text generate-content request.
    2. If successful, single real multimodal structured-output test using:
       - real uploaded civic incident image
       - real user problem description
       - GeminiComplaintDraft structured Pydantic schema
    """
    from google import genai
    from google.genai import types
    from app.config import settings
    from app.schemas.ai import GeminiComplaintDraft
    from app.agent.gemini_agent import SYSTEM_INSTRUCTION
    from pathlib import Path
    import time

    target_model = "gemini-3.1-flash-lite"
    api_key = (settings.GEMINI_API_KEY or "").strip()

    result = {
        "configured_model": settings.GEMINI_MODEL,
        "actually_tested_model": target_model,
        "api_key_configured": bool(api_key),
        "text_input_success": False,
        "image_input_success": False,
        "structured_output_success": False,
        "pydantic_success": False,
        "quota_exhausted": "UNKNOWN",
        "http_status": None,
        "actual_gemini_response": None,
        "error": None
    }

    if not api_key:
        result["error"] = "GEMINI_API_KEY is not configured"
        return result

    client = genai.Client(api_key=api_key)

    # Step 1: ONE minimal REAL generate-content request
    try:
        t0 = time.perf_counter()
        minimal_resp = client.models.generate_content(
            model=target_model,
            contents="Say 'CIVICFLOW_OK'",
            config=types.GenerateContentConfig(max_output_tokens=10, temperature=0.0)
        )
        t_minimal = (time.perf_counter() - t0) * 1000.0
        minimal_text = getattr(minimal_resp, "text", "").strip()
        result["text_input_success"] = True
        result["minimal_text_latency_ms"] = round(t_minimal, 2)
        result["minimal_text_output"] = minimal_text
        result["quota_exhausted"] = "NO"
        result["http_status"] = 200
    except Exception as me:
        err_str = str(me)
        result["error"] = f"Minimal text test failed: {err_str}"
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            result["quota_exhausted"] = "YES"
            result["http_status"] = 429
        elif "404" in err_str or "NOT_FOUND" in err_str:
            result["http_status"] = 404
        else:
            result["http_status"] = 500
        return result

    # Step 2: ONE REAL multimodal structured-output test
    upload_dir = Path(__file__).resolve().parent.parent / "uploads" / "complaints"
    test_image_path = upload_dir / "803038e39cd84f87bcc3c36f63cc7605.jpg"
    if not test_image_path.exists():
        result["error"] = "Evidence test image not found on disk"
        return result

    image_bytes = test_image_path.read_bytes()
    citizen_problem = "Deep roadway depression pothole filled with water and loose gravel on the street."

    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiComplaintDraft,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=600
        )
        prompt_text = (
            f"Please analyze the attached civic incident photograph and citizen report.\n\n"
            f"--- CITIZEN SUPPLIED INFORMATION ---\n"
            f"Citizen Problem Statement: \"\"\"{citizen_problem}\"\"\"\n"
            f"------------------------------------\n"
            f"Synthesize the structured draft according to the GeminiComplaintDraft specification."
        )

        t_start_multi = time.perf_counter()
        multi_resp = client.models.generate_content(
            model=target_model,
            contents=[image_part, prompt_text],
            config=config
        )
        t_multi = (time.perf_counter() - t_start_multi) * 1000.0

        result["image_input_success"] = True
        result["multimodal_latency_ms"] = round(t_multi, 2)

        # Parse & Validate with Pydantic
        draft = None
        if hasattr(multi_resp, "parsed") and multi_resp.parsed:
            if isinstance(multi_resp.parsed, GeminiComplaintDraft):
                draft = multi_resp.parsed
            elif isinstance(multi_resp.parsed, dict):
                draft = GeminiComplaintDraft.model_validate(multi_resp.parsed)
        elif hasattr(multi_resp, "text") and multi_resp.text:
            cleaned = multi_resp.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            draft = GeminiComplaintDraft.model_validate_json(cleaned)

        if draft:
            result["structured_output_success"] = True
            result["pydantic_success"] = True
            result["actual_gemini_response"] = draft.model_dump()
            result["quota_exhausted"] = "NO"
            result["http_status"] = 200
        else:
            result["structured_output_success"] = False
            result["pydantic_success"] = False
            result["error"] = "Gemini returned empty or non-parseable structured output"

    except Exception as multi_err:
        err_str = str(multi_err)
        result["error"] = f"Multimodal test failed: {err_str}"
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            result["quota_exhausted"] = "YES"
            result["http_status"] = 429
        elif "404" in err_str or "NOT_FOUND" in err_str:
            result["http_status"] = 404
        else:
            result["http_status"] = 500

    return result






