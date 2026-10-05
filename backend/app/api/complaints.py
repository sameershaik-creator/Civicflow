"""
Complaint Intake API Endpoints for CivicFlow (Phase 4).

Endpoints:
- POST /api/v1/complaints/analyze: Citizen intake & media upload pipeline (preserves raw evidence as DRAFT).
- GET  /api/v1/complaints: List authenticated citizen's complaints (or all complaints for admin).
- GET  /api/v1/complaints/{id}: Retrieve single complaint with backend-enforced ownership.
"""

import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, LocationStatus
from app.models.notification import Notification
from app.schemas.complaint import ComplaintResponse, ComplaintDraftUpdate
from app.api.deps import get_current_user, check_resource_ownership
from app.services import media_service, geocoding_service
from app.schemas.ai import GeminiComplaintDraft
from app.schemas.location import LocationVerificationResponse
from app.agent import gemini_agent
from app.agent.gemini_agent import (
    GeminiConfigurationError,
    GeminiAnalysisError,
    GeminiQuotaError,
    GeminiSafetyError,
    GeminiTimeoutError,
    GeminiNetworkError,
    GeminiServerError,
    GeminiModelNotFoundError
)

logger = logging.getLogger("civicflow.api.complaints")

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post(
    "/analyze",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Citizen complaint intake with image upload",
    description="Creates a complaint intake draft and stores original physical evidence. NOTE: AI analysis is deferred to Phase 5; ai_* and final_* fields remain NULL."
)
async def create_complaint_intake(
    image: UploadFile = File(..., description="Uploaded civic incident evidence image"),
    original_problem: Optional[str] = Form(None, description="Citizen problem description"),
    description: Optional[str] = Form(None, description="Alternative field for citizen problem description"),
    original_address: Optional[str] = Form(None, description="Citizen address hint"),
    address: Optional[str] = Form(None, description="Alternative field for citizen address hint"),
    original_latitude: Optional[float] = Form(None, description="Device GPS latitude"),
    latitude: Optional[float] = Form(None, description="Alternative field for GPS latitude"),
    original_longitude: Optional[float] = Form(None, description="Device GPS longitude"),
    longitude: Optional[float] = Form(None, description="Alternative field for GPS longitude"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Intake a new citizen complaint:
    1. Enforces authentication via JWT.
    2. Validates and stores the evidence image in the complaints upload directory.
    3. Normalizes and validates problem description (required).
    4. Validates GPS coordinates if provided.
    5. Preserves original citizen input without alteration.
    6. Ensures ai_* and final_* fields remain NULL (Phase 4 boundary).
    7. Stores initial status as DRAFT.
    """
    # 1. Validate problem description
    problem_text = (original_problem or description or "").strip()
    if not problem_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem description ('original_problem' or 'description') is required."
        )

    # 2. Validate coordinates if provided
    lat = original_latitude if original_latitude is not None else latitude
    lng = original_longitude if original_longitude is not None else longitude

    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be between -90.0 and 90.0 degrees."
        )
    if lng is not None and not (-180.0 <= lng <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Longitude must be between -180.0 and 180.0 degrees."
        )

    # 3. Securely validate and persist the uploaded image
    image_url, _ = await media_service.save_uploaded_image(image)

    # 4. Determine location status
    if lat is not None and lng is not None:
        loc_status = LocationStatus.COORDINATES_ATTACHED.value
    else:
        loc_status = LocationStatus.NO_LOCATION.value

    # 5. Normalize address
    addr_text = (original_address or address or "").strip() or None

    now = datetime.now(timezone.utc)

    # 6. Create Complaint entity strictly associating authenticated user
    new_complaint = Complaint(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        image_url=image_url,
        original_problem=problem_text,
        original_address=addr_text,
        original_latitude=lat,
        original_longitude=lng,
        # AI fields strictly remain NULL in Phase 4
        ai_problem=None,
        ai_address=None,
        ai_summary=None,
        # Final fields strictly remain NULL in Phase 4
        final_problem=None,
        final_address=None,
        final_summary=None,
        # Telemetry coordinates mirrored for query performance
        latitude=lat,
        longitude=lng,
        place_id=None,
        map_url=geocoding_service.build_map_url(lat, lng) if (lat is not None and lng is not None) else None,
        location_status=loc_status,
        status=ComplaintStatus.DRAFT.value,
        admin_reason=None,
        created_at=now,
        updated_at=now,
    )

    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)

    logger.info("Complaint created: ID=%s, User=%s", new_complaint.id, current_user.id)
    return new_complaint


@router.get(
    "",
    response_model=List[ComplaintResponse],
    status_code=status.HTTP_200_OK,
    summary="List complaints",
    description="Returns complaints belonging to the authenticated citizen. Administrators can view all complaints."
)
def list_complaints(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List complaints:
    - Citizens can view only their own complaints.
    - Administrators can view all submitted complaints.
    """
    is_admin = (
        current_user.role == UserRole.ADMIN.value or
        current_user.role == UserRole.ADMIN
    )
    if is_admin:
        complaints = db.query(Complaint).order_by(Complaint.created_at.desc()).all()
    else:
        complaints = (
            db.query(Complaint)
            .filter(Complaint.user_id == current_user.id)
            .order_by(Complaint.created_at.desc())
            .all()
        )
    return complaints


@router.get(
    "/{id}",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single complaint by ID",
    description="Retrieves a complaint with backend-enforced ownership. Citizens can access only their own complaints."
)
def get_complaint(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve single complaint by ID:
    - 401 if unauthenticated.
    - 404 if complaint does not exist.
    - 403 if citizen attempts to view another citizen's complaint.
    - 200 if citizen views own complaint or if administrator.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    return complaint


@router.get(
    "/{complaint_id}/image",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complaint evidence image with authorization",
    description="Streams the complaint evidence image file only after verifying user identity and ownership (or admin role). Blocks unauthenticated and unauthorized access."
)
def get_complaint_image(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authorized evidence image stream:
    - 401 if unauthenticated.
    - 404 if complaint does not exist.
    - 403 if citizen attempts to view another citizen's evidence image.
    - 200 streams actual image file if owner citizen or administrator.
    - Prevents arbitrary filesystem path traversal.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce row-level ownership: allowed only for owner or administrator
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    if not complaint.image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint does not have an associated image"
        )

    if complaint.image_url.startswith("http://") or complaint.image_url.startswith("https://"):
        image_bytes, media_type = media_service.read_image_bytes(complaint.image_url)
        return Response(content=image_bytes, media_type=media_type)

    # Securely resolve file within the dedicated upload directory
    filename = os.path.basename(complaint.image_url)
    upload_dir = media_service.get_upload_directory().resolve()
    image_path = (upload_dir / filename).resolve()

    # Verify path remains strictly inside the upload directory
    if not str(image_path).startswith(str(upload_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image path detected"
        )

    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on disk"
        )

    ext = image_path.suffix.lower()
    media_type = "image/jpeg"
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(
        path=str(image_path),
        media_type=media_type,
        filename=filename
    )


@router.post(
    "/{complaint_id}/analyze",
    response_model=GeminiComplaintDraft,
    status_code=status.HTTP_200_OK,
    summary="Generate Gemini multimodal complaint draft",
    description="Processes the uploaded physical evidence image and citizen problem description through the Gemini multimodal agent to produce a structured complaint draft and update the complaint to AI_GENERATED."
)
async def analyze_complaint_with_gemini(
    complaint_id: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Multimodal AI complaint analysis pipeline:
    1. Authenticates current user via JWT.
    2. Loads complaint by ID from database.
    3. Enforces ownership: only complaint owner or administrator is authorized.
    4. Idempotency: If already AI_GENERATED, returns the existing structured draft.
    5. Reads physical evidence image from disk securely.
    6. Calls real configured Gemini multimodal AI agent with strict evidence rules.
    7. Validates structured output via Pydantic.
    8. Persists AI results (ai_problem, ai_summary) and transitions DRAFT -> AI_GENERATED.
    9. Sets forensic latency headers (T2..T7) and returns validated GeminiComplaintDraft.
    """
    import time
    t2_fastapi_receive = time.perf_counter()

    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # 3. Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    # 4. Idempotency check: return existing draft if already processed
    if complaint.status in (ComplaintStatus.AI_GENERATED.value, ComplaintStatus.UNDER_REVIEW.value):
        cached_draft = gemini_agent.load_ai_draft_from_disk(complaint.id)
        if cached_draft:
            logger.info("Returning cached AI draft for complaint %s (idempotent)", complaint.id)
            return cached_draft

    if complaint.status in (ComplaintStatus.SUBMITTED.value, ComplaintStatus.ACCEPTED.value, ComplaintStatus.REJECTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot run AI analysis on complaint in status '{complaint.status}'. State is locked."
        )

    # 5. Verify and read image from storage
    if not complaint.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint does not have an attached evidence image."
        )

    image_bytes, mime_type = media_service.read_image_bytes(complaint.image_url)

    # 6. Call Real Gemini AI Agent with Latency Tracking (T3..T5)
    try:
        draft, timing = gemini_agent.analyze_complaint_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            citizen_problem=complaint.original_problem,
            address=complaint.original_address,
            latitude=complaint.original_latitude,
            longitude=complaint.original_longitude,
            return_latency=True
        )
    except GeminiQuotaError as e:
        logger.warning("Gemini quota error (HTTP 429): %s", e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except GeminiTimeoutError as e:
        logger.warning("Gemini timeout error (HTTP 504): %s", e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except GeminiNetworkError as e:
        logger.error("Gemini network error (HTTP 503): %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except GeminiServerError as e:
        logger.error("Gemini server error (HTTP 502): %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except GeminiModelNotFoundError as e:
        logger.error("Gemini model not found (HTTP 404): %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GeminiSafetyError as e:
        logger.warning("Gemini safety error (HTTP 422): %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded evidence triggered safety filters and could not be analyzed."
        )
    except GeminiConfigurationError as e:
        logger.error("Gemini configuration error (HTTP 503): %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI complaint analysis service is not properly configured."
        )
    except GeminiAnalysisError as e:
        logger.error("Gemini analysis error (HTTP 502): %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI complaint analysis failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unhandled error during Gemini analysis: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during AI complaint drafting."
        )

    # 7. Persist AI results into database (T5 -> T6)
    t6_db_start = time.perf_counter()
    complaint.ai_problem = draft.observed_issue
    complaint.ai_summary = draft.formal_summary
    complaint.ai_address = None  # Preserved semantic distinction — not fabricated
    complaint.status = ComplaintStatus.AI_GENERATED.value
    complaint.updated_at = datetime.now(timezone.utc)

    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    t6_db_end = time.perf_counter()
    db_ms = (t6_db_end - t6_db_start) * 1000.0

    # 8. Persist sidecar structured draft for idempotency
    try:
        gemini_agent.save_ai_draft_to_disk(complaint.id, draft)
    except Exception as disk_err:
        logger.warning("Failed to save AI draft sidecar to disk: %s", disk_err)

    t7_fastapi_send = time.perf_counter()
    total_backend_ms = (t7_fastapi_send - t2_fastapi_receive) * 1000.0
    gemini_ms = timing.get("t3_to_t4_gemini_ms", 0.0)
    pydantic_ms = timing.get("t4_to_t5_pydantic_ms", 0.0)

    # Set diagnostic timing headers
    response.headers["X-Latency-Gemini-Ms"] = str(round(gemini_ms, 2))
    response.headers["X-Latency-Pydantic-Ms"] = str(round(pydantic_ms, 2))
    response.headers["X-Latency-DB-Ms"] = str(round(db_ms, 2))
    response.headers["X-Latency-Backend-Total-Ms"] = str(round(total_backend_ms, 2))

    logger.info(
        "LATENCY FORENSIC [Complaint %s]: Gemini=%.2f ms, Pydantic=%.2f ms, DB=%.2f ms, Total_Backend=%.2f ms",
        complaint.id, gemini_ms, pydantic_ms, db_ms, total_backend_ms
    )
    logger.info("Complaint %s successfully transitioned to AI_GENERATED", complaint.id)
    return draft


@router.post(
    "/{complaint_id}/location/verify",
    response_model=LocationVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify complaint location and detect geographic discrepancy",
    description="Forward geocodes entered address, reverse geocodes device GPS coordinates, calculates geodesic distance, detects mismatches, and persists canonical coordinates and location status."
)
def verify_complaint_location(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Geographic verification pipeline:
    1. Authenticates current user via JWT.
    2. Loads complaint by ID from database (404 if not found).
    3. Enforces row-level ownership: only complaint owner or admin authorized (403 if foreign).
    4. Evaluates original_address and original coordinates via geocoding_service.
    5. Calculates geodesic distance via Haversine formula and checks mismatch threshold.
    6. Persists derived geographic fields (latitude, longitude, place_id, map_url, location_status).
    7. Preserves raw telemetry (original_latitude, original_longitude) and AI/final fields untouched.
    8. Returns structured LocationVerificationResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    if complaint.status in (ComplaintStatus.SUBMITTED.value, ComplaintStatus.ACCEPTED.value, ComplaintStatus.REJECTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot re-verify location when complaint is in locked status '{complaint.status}'."
        )

    # Perform geographic verification
    result = geocoding_service.verify_complaint_location(
        original_address=complaint.original_address,
        original_latitude=complaint.original_latitude,
        original_longitude=complaint.original_longitude
    )

    # Persist derived geographic verification results
    complaint.latitude = result.get("latitude")
    complaint.longitude = result.get("longitude")
    complaint.place_id = result.get("place_id")
    complaint.map_url = result.get("map_url")
    complaint.location_status = result.get("location_status")
    complaint.updated_at = datetime.now(timezone.utc)

    # Provenance fields (original_*, ai_*, final_*) and status remain UNCHANGED
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    logger.info(
        "Complaint %s location verified: status=%s, distance=%s",
        complaint.id,
        complaint.location_status,
        result.get("distance_meters")
    )
    return LocationVerificationResponse(**result)


@router.get(
    "/{complaint_id}/location",
    response_model=LocationVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verified location details for complaint",
    description="Retrieves persisted geographic verification details, canonical coordinates, map URL, and verification status."
)
def get_complaint_location(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the geographic verification details for a complaint:
    - Enforces authentication and row-level ownership.
    - If location has not yet been verified, performs on-the-fly verification and persists results.
    - Returns structured LocationVerificationResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    # If map_url is not set but original data exists, verify and persist
    if not complaint.map_url and (complaint.original_latitude is not None or complaint.original_address):
        result = geocoding_service.verify_complaint_location(
            original_address=complaint.original_address,
            original_latitude=complaint.original_latitude,
            original_longitude=complaint.original_longitude
        )
        complaint.latitude = result.get("latitude")
        complaint.longitude = result.get("longitude")
        complaint.place_id = result.get("place_id")
        complaint.map_url = result.get("map_url")
        complaint.location_status = result.get("location_status")
        complaint.updated_at = datetime.now(timezone.utc)
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return LocationVerificationResponse(**result)

    # Return persisted geographic status
    is_verified = (complaint.location_status == LocationStatus.VERIFIED.value)
    is_mismatch = (complaint.location_status in (LocationStatus.MISMATCH.value, LocationStatus.MISMATCH_SUSPECTED.value))

    return LocationVerificationResponse(
        location_status=complaint.location_status or LocationStatus.COORDINATES_ATTACHED.value,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        place_id=complaint.place_id,
        map_url=complaint.map_url,
        distance_meters=None,
        address_match=True if is_verified else (False if is_mismatch else None),
        geocoded_address=complaint.original_address,
        reverse_geocoded_address=None,
        message=f"Location status: {complaint.location_status}"
    )


@router.get(
    "/{complaint_id}/ai-draft",
    response_model=GeminiComplaintDraft,
    status_code=status.HTTP_200_OK,
    summary="Get structured AI complaint draft",
    description="Retrieves the Gemini multimodal structured draft for a complaint. Enforces row-level ownership."
)
def get_complaint_ai_draft(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve structured AI complaint draft:
    - 401 if unauthenticated
    - 404 if complaint does not exist
    - 403 if citizen attempts to view another citizen's complaint
    - 404 if AI draft has not been generated yet
    - 200 with validated GeminiComplaintDraft
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    # 1. Attempt to load sidecar JSON from disk
    cached_draft = gemini_agent.load_ai_draft_from_disk(complaint.id)
    if cached_draft:
        return cached_draft

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="AI draft has not been generated for this complaint yet or structured sidecar is unavailable."
    )



@router.put(
    "/{complaint_id}/draft",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    summary="Update complaint draft with citizen human review",
    description="Saves citizen-edited draft fields (final_problem, final_address, final_summary) and transitions complaint state strictly to UNDER_REVIEW. Preserves original evidence and AI reasoning immutable."
)
def update_complaint_draft(
    complaint_id: str,
    payload: ComplaintDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Human Review & Citizen Draft Editing (Phase 7):
    1. Authenticates current user via JWT.
    2. Loads complaint by ID (404 if not found).
    3. Enforces row-level ownership: only owner or administrator authorized (403 if foreign).
    4. Validates FSM transition:
       - Allowed from: AI_GENERATED, UNDER_REVIEW
       - Disallowed from DRAFT (AI draft not yet created -> 400 Bad Request)
       - Disallowed from SUBMITTED, ACCEPTED, REJECTED (terminal/locked states -> 400 Bad Request)
    5. Validates payload via Pydantic (non-empty final_problem).
    6. Updates citizen-approved fields strictly: final_problem, final_address, final_summary.
    7. Transitions status to UNDER_REVIEW.
    8. Strictly preserves original citizen evidence (original_problem, original_address, original_latitude, original_longitude, image_url) untouched.
    9. Strictly preserves AI analysis layer (ai_problem, ai_address, ai_summary) untouched.
    10. Strictly preserves deterministic geographic data (latitude, longitude, map_url, location_status) untouched.
    11. Rejects any attempt to manipulate admin fields or set prohibited states (SUBMITTED/ACCEPTED/REJECTED).
    12. Returns updated ComplaintResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    # Enforce FSM state transition rules
    if complaint.status == ComplaintStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint must have an AI draft generated before human review."
        )

    allowed_states = {ComplaintStatus.AI_GENERATED.value, ComplaintStatus.UNDER_REVIEW.value}
    if complaint.status not in allowed_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit draft when complaint is in status '{complaint.status}'. Editable statuses: AI_GENERATED, UNDER_REVIEW."
        )

    # Update citizen-approved final draft fields
    complaint.final_problem = payload.final_problem
    complaint.final_address = payload.final_address
    complaint.final_summary = payload.final_summary

    # Transition strictly to UNDER_REVIEW
    complaint.status = ComplaintStatus.UNDER_REVIEW.value
    complaint.updated_at = datetime.now(timezone.utc)

    # Note: original_*, ai_*, and geographic fields remain strictly untouched
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    logger.info("Complaint %s draft updated by user %s; status transitioned to UNDER_REVIEW", complaint.id, current_user.id)
    return complaint


@router.post(
    "/{complaint_id}/submit",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    summary="Citizen final complaint submission",
    description="Transitions complaint from UNDER_REVIEW to SUBMITTED. Generates server-side submitted_at UTC timestamp, locks complaint from further edits, and enforces row-level ownership."
)
def submit_complaint(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Citizen Final Submission Pipeline (Phase 8):
    1. Authenticates current user via JWT (401 if unauthenticated).
    2. Loads complaint by ID from database (404 if not found).
    3. Enforces row-level ownership: only owner or administrator authorized (403 if foreign).
    4. Validates FSM transition:
       - Only UNDER_REVIEW is permitted to transition to SUBMITTED.
       - Rejects DRAFT (400 Bad Request): Must undergo AI analysis and review.
       - Rejects AI_GENERATED (400 Bad Request): Must be reviewed in UNDER_REVIEW first.
       - Rejects SUBMITTED (400 Bad Request): Complaint has already been submitted and cannot be resubmitted.
       - Rejects ACCEPTED, REJECTED (400 Bad Request): Cannot submit locked/adjudicated complaint.
    5. Validates final content:
       - final_problem must exist and must not be empty or whitespace-only (422 Unprocessable Entity).
    6. Generates server-side submitted_at UTC timestamp.
    7. Atomically transitions status to SUBMITTED and updates timestamps.
    8. Preserves original citizen evidence (original_*) and AI reasoning (ai_*) strictly immutable.
    9. Preserves final citizen-reviewed fields (final_*) exactly as saved in Phase 7.
    10. Commits database transaction (rolls back on failure).
    11. Returns updated ComplaintResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # 3. Enforce row-level ownership
    check_resource_ownership(resource_owner_id=complaint.user_id, current_user=current_user)

    # 4. Enforce strict FSM transition rules
    if complaint.status == ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint has already been submitted and cannot be submitted again."
        )

    if complaint.status == ComplaintStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is still in DRAFT status and must undergo AI analysis and human review before submission."
        )

    if complaint.status == ComplaintStatus.AI_GENERATED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint must be reviewed and saved in UNDER_REVIEW status before final submission."
        )

    if complaint.status in (ComplaintStatus.ACCEPTED.value, ComplaintStatus.REJECTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit complaint in terminal status '{complaint.status}'."
        )

    if complaint.status != ComplaintStatus.UNDER_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition. Cannot submit complaint from status '{complaint.status}'."
        )

    # 5. Final content validation: final_problem must be present and non-empty
    if not complaint.final_problem or not complaint.final_problem.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complaint cannot be submitted without a confirmed problem description (final_problem)."
        )

    # 6. Generate server-side UTC timestamps and set SUBMITTED status
    now = datetime.now(timezone.utc)
    complaint.status = ComplaintStatus.SUBMITTED.value
    complaint.submitted_at = now
    complaint.updated_at = now

    # 7. Atomic transaction commit
    try:
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit final submission for complaint %s: %s", complaint.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during final submission."
        )

    logger.info(
        "Complaint %s successfully submitted by user %s at %s; state transitioned to SUBMITTED",
        complaint.id,
        current_user.id,
        now.isoformat()
    )
    return complaint


@router.delete(
    "/{complaint_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete citizen-owned complaint and associated data",
    description="Permanently deletes a complaint belonging strictly to the authenticated citizen. Atomically cleans up associated notifications, physical evidence files, and sidecar drafts."
)
def delete_complaint(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a complaint owned by the current authenticated citizen:
    1. Authenticates current user (401 if unauthenticated).
    2. Retrieves complaint from DB (404 if not found).
    3. Enforces row-level ownership: current_user.id must match complaint.user_id (403 if foreign/unauthorized).
    4. Cleans up associated notifications atomically within transaction.
    5. Deletes complaint record from DB within transaction.
    6. Cleans up physical evidence image file from disk (post-commit).
    7. Cleans up sidecar draft JSON from disk (post-commit).
    8. Returns 200 OK with success confirmation.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce strict row-level ownership: only the owner citizen may delete
    if complaint.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this complaint."
        )

    image_url = complaint.image_url

    try:
        # 1. Delete associated notifications atomically
        db.query(Notification).filter(Notification.complaint_id == str(complaint_id)).delete(synchronize_session=False)

        # 2. Delete complaint record
        db.delete(complaint)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete complaint %s from database: %s", complaint_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete complaint due to database error."
        )

    # 3. Clean up physical evidence image file on disk (post-commit)
    if image_url:
        try:
            media_service.delete_uploaded_image(image_url)
        except Exception as img_err:
            logger.warning("Failed to clean up image file for deleted complaint %s: %s", complaint_id, img_err)

    # 4. Clean up sidecar AI draft file on disk (post-commit)
    try:
        gemini_agent.delete_ai_draft_from_disk(str(complaint_id))
    except Exception as draft_err:
        logger.warning("Failed to clean up sidecar draft for deleted complaint %s: %s", complaint_id, draft_err)

    logger.info("Complaint %s successfully deleted by owner %s", complaint_id, current_user.id)
    return {
        "status": "success",
        "message": "Complaint deleted successfully.",
        "deleted_complaint_id": str(complaint_id)
    }



