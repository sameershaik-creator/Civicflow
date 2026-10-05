from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from app.models.complaint import ComplaintStatus, LocationStatus


class ComplaintBase(BaseModel):
    original_problem: str
    original_address: Optional[str] = None
    original_latitude: Optional[float] = None
    original_longitude: Optional[float] = None


class ComplaintDraftUpdate(BaseModel):
    final_problem: str
    final_address: Optional[str] = None
    final_summary: Optional[str] = None

    @field_validator("final_problem")
    @classmethod
    def validate_final_problem(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("final_problem cannot be empty.")
        return v.strip()

    @field_validator("final_address", "final_summary")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    image_url: str

    # Raw citizen input
    original_problem: str
    original_address: Optional[str] = None
    original_latitude: Optional[float] = None
    original_longitude: Optional[float] = None

    # AI Draft
    ai_problem: Optional[str] = None
    ai_address: Optional[str] = None
    ai_summary: Optional[str] = None

    # Final Citizen Approved
    final_problem: Optional[str] = None
    final_address: Optional[str] = None
    final_summary: Optional[str] = None

    # Location & Mapping
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    map_url: Optional[str] = None
    location_status: LocationStatus

    # FSM State & Adjudication
    status: ComplaintStatus
    admin_reason: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
