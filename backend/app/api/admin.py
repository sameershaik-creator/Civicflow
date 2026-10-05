"""
Municipal Administrator Adjudication API Router (Phase 9).

Provides:
- GET /api/v1/admin/complaints: List complaints awaiting adjudication (SUBMITTED queue).
- GET /api/v1/admin/complaints/{complaint_id}: Full evidence package inspection.
- POST /api/v1/admin/complaints/{complaint_id}/accept: Transition SUBMITTED -> ACCEPTED.
- POST /api/v1/admin/complaints/{complaint_id}/reject: Transition SUBMITTED -> REJECTED with validated reason.

Enforces:
- Strict role-based access control (require_admin).
- Row-level and model-level provenance immutability.
- Server-side UTC timestamp generation (decided_at).
- Database transaction atomicity with rollback.
- Terminal state locking (no further transitions after ACCEPTED or REJECTED).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.notification import Notification
from app.models.user import User
from app.api.deps import require_admin
from app.agent import gemini_agent
from app.schemas.admin import (
    AdminComplaintListItem,
    AdminComplaintDetailResponse,
    ComplaintRejectRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/complaints", tags=["admin"])


ADJUDICABLE_STATUSES = (
    ComplaintStatus.SUBMITTED.value,
    ComplaintStatus.ACCEPTED.value,
    ComplaintStatus.REJECTED.value,
)

CITIZEN_DRAFT_STATUSES = (
    ComplaintStatus.DRAFT.value,
    ComplaintStatus.AI_GENERATED.value,
    ComplaintStatus.UNDER_REVIEW.value,
)


def _build_detail_response(complaint: Complaint) -> AdminComplaintDetailResponse:
    """Helper to assemble the complete evidence package for a complaint."""
    # Attempt to load structured sidecar draft from disk
    cached_draft = gemini_agent.load_ai_draft_from_disk(complaint.id)
    if cached_draft:
        category = cached_draft.category
        observed_issue = cached_draft.observed_issue
        citizen_claim = cached_draft.citizen_claim
        formal_summary = cached_draft.formal_summary
        urgency_level = cached_draft.urgency_level
        warnings = cached_draft.warnings
    elif complaint.ai_problem or complaint.ai_summary:
        category = "Civic Issue"
        observed_issue = complaint.ai_problem
        citizen_claim = complaint.original_problem
        formal_summary = complaint.ai_summary
        urgency_level = "MEDIUM"
        warnings = []
    else:
        category = None
        observed_issue = None
        citizen_claim = None
        formal_summary = None
        urgency_level = None
        warnings = []

    citizen_name = complaint.user.name if complaint.user else None
    citizen_email = complaint.user.email if complaint.user else None

    return AdminComplaintDetailResponse(
        id=complaint.id,
        user_id=complaint.user_id,
        image_url=complaint.image_url,
        original_problem=complaint.original_problem,
        original_address=complaint.original_address,
        original_latitude=complaint.original_latitude,
        original_longitude=complaint.original_longitude,
        ai_problem=complaint.ai_problem,
        ai_address=complaint.ai_address,
        ai_summary=complaint.ai_summary,
        category=category,
        observed_issue=observed_issue,
        citizen_claim=citizen_claim,
        formal_summary=formal_summary,
        urgency_level=urgency_level,
        warnings=warnings,
        final_problem=complaint.final_problem,
        final_address=complaint.final_address,
        final_summary=complaint.final_summary,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        place_id=complaint.place_id,
        map_url=complaint.map_url,
        location_status=complaint.location_status,
        status=complaint.status,
        admin_reason=complaint.admin_reason,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        submitted_at=complaint.submitted_at,
        decided_at=complaint.decided_at,
        citizen_name=citizen_name,
        citizen_email=citizen_email,
    )


@router.get(
    "",
    response_model=List[AdminComplaintListItem],
    status_code=status.HTTP_200_OK,
    summary="List complaints for administrative triage",
    description="Retrieves complaints for municipal administration. Default queue focuses on SUBMITTED complaints awaiting review."
)
def list_admin_complaints(
    status_filter: Optional[str] = Query(
        default=ComplaintStatus.SUBMITTED.value,
        alias="status",
        description="Filter by complaint status: SUBMITTED, ACCEPTED, REJECTED, or ALL_ADJUDICABLE."
    ),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List complaints for admin dashboard:
    - 401 if unauthenticated.
    - 403 if authenticated citizen.
    - 200 with list of complaints if administrator.
    - Strictly limits to adjudicable complaints (SUBMITTED, ACCEPTED, REJECTED).
    - Citizen drafting states (DRAFT, AI_GENERATED, UNDER_REVIEW) are forbidden.
    - Returns real database records; empty list if 0 records (truthful zero-demo-data).
    """
    clean_filter = (status_filter or ComplaintStatus.SUBMITTED.value).strip().upper()

    # Reject attempts to query citizen-only draft statuses
    if clean_filter in CITIZEN_DRAFT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status '{clean_filter}' is a citizen drafting state and cannot be accessed via the administrative adjudication queue."
        )

    query = db.query(Complaint)

    if clean_filter in ("ALL", "ALL_ADJUDICABLE"):
        query = query.filter(Complaint.status.in_(ADJUDICABLE_STATUSES))
    elif clean_filter in ADJUDICABLE_STATUSES:
        query = query.filter(Complaint.status == clean_filter)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status filter '{status_filter}'. Admin adjudication queue only supports: SUBMITTED, ACCEPTED, REJECTED, or ALL_ADJUDICABLE."
        )

    complaints = query.order_by(
        Complaint.submitted_at.desc(),
        Complaint.created_at.desc()
    ).all()

    items: List[AdminComplaintListItem] = []
    for c in complaints:
        draft = gemini_agent.load_ai_draft_from_disk(c.id)
        cat = draft.category if draft else ("Civic Issue" if (c.ai_problem or c.ai_summary) else None)
        urg = draft.urgency_level if draft else ("MEDIUM" if (c.ai_problem or c.ai_summary) else None)

        items.append(
            AdminComplaintListItem(
                id=c.id,
                user_id=c.user_id,
                status=c.status,
                original_problem=c.original_problem,
                original_address=c.original_address,
                final_problem=c.final_problem,
                final_address=c.final_address,
                category=cat,
                urgency_level=urg,
                location_status=c.location_status,
                latitude=c.latitude,
                longitude=c.longitude,
                map_url=c.map_url,
                image_url=c.image_url,
                created_at=c.created_at,
                submitted_at=c.submitted_at,
                decided_at=c.decided_at,
                admin_reason=c.admin_reason,
                citizen_name=c.user.name if c.user else None,
                citizen_email=c.user.email if c.user else None,
            )
        )

    return items


@router.get(
    "/{complaint_id}",
    response_model=AdminComplaintDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete complaint evidence package for adjudication",
    description="Retrieves raw evidence, AI interpretation, citizen final version, geographic verification, and workflow state."
)
def get_admin_complaint_detail(
    complaint_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve complaint detail for admin adjudication:
    - 401 if unauthenticated.
    - 403 if authenticated citizen.
    - 404 if complaint not found.
    - 404 if complaint has not reached an adjudicable state (SUBMITTED, ACCEPTED, REJECTED).
    - 200 with complete evidence package for administrator.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Strictly reject citizen drafting states (DRAFT, AI_GENERATED, UNDER_REVIEW)
    if complaint.status not in ADJUDICABLE_STATUSES:
        logger.warning(
            "Admin %s attempted to inspect non-adjudicable complaint %s with status %s",
            current_admin.id,
            complaint.id,
            complaint.status
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint has not been submitted for municipal adjudication."
        )

    return _build_detail_response(complaint)


@router.post(
    "/{complaint_id}/accept",
    response_model=AdminComplaintDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept submitted complaint for municipal action",
    description="Transitions complaint from SUBMITTED to ACCEPTED. Generates server-side UTC decided_at timestamp and locks complaint."
)
def accept_complaint(
    complaint_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Municipal Complaint Acceptance (Phase 9):
    1. Authenticates admin via JWT (401 unauth, 403 citizen).
    2. Loads complaint by ID (404 if not found).
    3. Enforces FSM transition:
       - Only SUBMITTED complaints may be accepted.
       - Rejects DRAFT, AI_GENERATED, UNDER_REVIEW (400 Bad Request).
       - Rejects duplicate accept on ACCEPTED (400 Bad Request).
       - Rejects accept on REJECTED (400 Bad Request: terminal lock).
    4. Generates server-side decided_at in UTC.
    5. Sets status = ACCEPTED.
    6. Preserves original_*, ai_*, and final_* provenance layers strictly immutable.
    7. Commits transaction atomically with rollback on error.
    8. Returns updated AdminComplaintDetailResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce strict FSM transition rules
    if complaint.status == ComplaintStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint has already been accepted and cannot be accepted again."
        )

    if complaint.status == ComplaintStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot accept a complaint that has already been rejected (terminal state)."
        )

    if complaint.status != ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept complaint in status '{complaint.status}'. Only SUBMITTED complaints may be accepted."
        )

    now = datetime.now(timezone.utc)
    complaint.status = ComplaintStatus.ACCEPTED.value
    complaint.decided_at = now
    complaint.updated_at = now

    # Phase 10: Create persistent in-app notification for citizen owner
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=complaint.user_id,
        complaint_id=complaint.id,
        title="Complaint accepted",
        message="Your complaint has been accepted for administrative action.",
        is_read=False,
        created_at=now
    )

    try:
        db.add(complaint)
        db.add(notification)
        db.commit()
        db.refresh(complaint)
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit acceptance for complaint %s: %s", complaint.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during complaint acceptance."
        )

    logger.info(
        "Complaint %s successfully accepted by admin %s at %s; state transitioned to ACCEPTED",
        complaint.id,
        current_admin.id,
        now.isoformat()
    )
    return _build_detail_response(complaint)


@router.post(
    "/{complaint_id}/reject",
    response_model=AdminComplaintDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject submitted complaint with objective municipal reason",
    description="Transitions complaint from SUBMITTED to REJECTED. Requires meaningful admin_reason, generates server-side UTC decided_at timestamp, and locks complaint."
)
def reject_complaint(
    complaint_id: str,
    payload: ComplaintRejectRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Municipal Complaint Rejection (Phase 9):
    1. Authenticates admin via JWT (401 unauth, 403 citizen).
    2. Loads complaint by ID (404 if not found).
    3. Enforces FSM transition:
       - Only SUBMITTED complaints may be rejected.
       - Rejects DRAFT, AI_GENERATED, UNDER_REVIEW (400 Bad Request).
       - Rejects duplicate reject on REJECTED (400 Bad Request).
       - Rejects reject on ACCEPTED (400 Bad Request: terminal lock).
    4. Validates admin_reason: non-empty, non-whitespace, max 2000 chars (422 Unprocessable Entity).
    5. Generates server-side decided_at in UTC.
    6. Sets status = REJECTED and records admin_reason.
    7. Preserves original_*, ai_*, and final_* provenance layers strictly immutable.
    8. Commits transaction atomically with rollback on error.
    9. Returns updated AdminComplaintDetailResponse.
    """
    complaint = db.query(Complaint).filter(Complaint.id == str(complaint_id)).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Enforce strict FSM transition rules
    if complaint.status == ComplaintStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint has already been rejected and cannot be rejected again."
        )

    if complaint.status == ComplaintStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject a complaint that has already been accepted (terminal state)."
        )

    if complaint.status != ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject complaint in status '{complaint.status}'. Only SUBMITTED complaints may be rejected."
        )

    now = datetime.now(timezone.utc)
    complaint.status = ComplaintStatus.REJECTED.value
    complaint.admin_reason = payload.admin_reason
    complaint.decided_at = now
    complaint.updated_at = now

    # Phase 10: Create persistent in-app notification for citizen owner with actual admin reason
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=complaint.user_id,
        complaint_id=complaint.id,
        title="Complaint update",
        message=f"Your complaint was rejected. Reason: {payload.admin_reason}",
        is_read=False,
        created_at=now
    )

    try:
        db.add(complaint)
        db.add(notification)
        db.commit()
        db.refresh(complaint)
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit rejection for complaint %s: %s", complaint.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed during complaint rejection."
        )

    logger.info(
        "Complaint %s successfully rejected by admin %s at %s; state transitioned to REJECTED; reason=%s",
        complaint.id,
        current_admin.id,
        now.isoformat(),
        payload.admin_reason
    )
    return _build_detail_response(complaint)
