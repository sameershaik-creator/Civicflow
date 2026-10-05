"""
Pydantic Schemas for Municipal Administrator Adjudication (Phase 9).
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.complaint import ComplaintStatus, LocationStatus


class ComplaintRejectRequest(BaseModel):
    """
    Schema for administrator rejection request.
    Requires a non-empty, non-whitespace explanation.
    """
    admin_reason: str = Field(
        ...,
        description="Mandatory explanation stating the objective municipal rationale for rejection."
    )

    @field_validator("admin_reason")
    @classmethod
    def validate_admin_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Rejection reason cannot be empty or whitespace-only.")
        cleaned = v.strip()
        if len(cleaned) > 2000:
            raise ValueError("Rejection reason cannot exceed 2000 characters.")
        return cleaned


class AdminComplaintListItem(BaseModel):
    """
    Compact summary for administrative queue display.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: ComplaintStatus
    original_problem: str
    original_address: Optional[str] = None
    final_problem: Optional[str] = None
    final_address: Optional[str] = None
    category: Optional[str] = None
    urgency_level: Optional[str] = None
    location_status: LocationStatus
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_url: Optional[str] = None
    image_url: str
    created_at: datetime
    submitted_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    admin_reason: Optional[str] = None
    citizen_name: Optional[str] = None
    citizen_email: Optional[str] = None


class AdminComplaintDetailResponse(BaseModel):
    """
    Full provenance evidence package for municipal administrator review and adjudication.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    image_url: str

    # Layer 1: Raw Citizen Input
    original_problem: str
    original_address: Optional[str] = None
    original_latitude: Optional[float] = None
    original_longitude: Optional[float] = None

    # Layer 2: Gemini AI Analysis
    ai_problem: Optional[str] = None
    ai_address: Optional[str] = None
    ai_summary: Optional[str] = None
    category: Optional[str] = None
    observed_issue: Optional[str] = None
    citizen_claim: Optional[str] = None
    formal_summary: Optional[str] = None
    urgency_level: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    # Layer 3: Final Citizen Approved
    final_problem: Optional[str] = None
    final_address: Optional[str] = None
    final_summary: Optional[str] = None

    # Layer 4: Location & Mapping
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    map_url: Optional[str] = None
    location_status: LocationStatus

    # Workflow & Adjudication
    status: ComplaintStatus
    admin_reason: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None

    # Citizen Contact for Administration
    citizen_name: Optional[str] = None
    citizen_email: Optional[str] = None
