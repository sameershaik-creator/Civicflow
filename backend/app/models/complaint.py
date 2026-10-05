import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ComplaintStatus(str, Enum):
    """Finite State Machine states for complaints."""
    DRAFT = "DRAFT"
    AI_GENERATED = "AI_GENERATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class LocationStatus(str, Enum):
    """Geographic validation statuses."""
    COORDINATES_ATTACHED = "COORDINATES_ATTACHED"
    MISMATCH_SUSPECTED = "MISMATCH_SUSPECTED"
    MISMATCH = "MISMATCH"
    VERIFIED = "VERIFIED"
    GEOCODED = "GEOCODED"
    REVERSE_GEOCODED = "REVERSE_GEOCODED"
    NO_LOCATION = "NO_LOCATION"
    GEOCODING_FAILED = "GEOCODING_FAILED"
    REVERSE_GEOCODING_FAILED = "REVERSE_GEOCODING_FAILED"


class Complaint(Base):
    """
    Core Complaint entity preserving provenance across:
    1. Raw citizen submission (original_*)
    2. AI draft synthesis (ai_*)
    3. Human-reviewed & edited final report (final_*)
    4. Deterministic telemetry & geographic service data
    """
    __tablename__ = "complaints"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Physical Evidence Image
    image_url = Column(String(512), nullable=False)

    # Provenance Layer 1: Raw Citizen Input
    original_problem = Column(Text, nullable=False)
    original_address = Column(String(512), nullable=True)
    original_latitude = Column(Float, nullable=True)
    original_longitude = Column(Float, nullable=True)

    # Provenance Layer 2: Gemini AI Analysis
    ai_problem = Column(Text, nullable=True)
    ai_address = Column(String(512), nullable=True)
    ai_summary = Column(Text, nullable=True)

    # Provenance Layer 3: Citizen Reviewed & Edited Final Submission
    final_problem = Column(Text, nullable=True)
    final_address = Column(String(512), nullable=True)
    final_summary = Column(Text, nullable=True)

    # Geographic & Mapping Engine Details (Deterministic, NOT LLM-generated)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String(128), nullable=True)
    map_url = Column(String(512), nullable=True)
    location_status = Column(
        String(50),
        nullable=False,
        default=LocationStatus.COORDINATES_ATTACHED.value
    )

    # FSM State & Adjudication
    status = Column(
        String(30),
        nullable=False,
        default=ComplaintStatus.DRAFT.value,
        index=True
    )
    admin_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    submitted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    decided_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ORM Relationships
    user = relationship("User", back_populates="complaints")
    notifications = relationship("Notification", back_populates="complaint")

    def __repr__(self):
        return f"<Complaint id={self.id} user_id={self.user_id} status={self.status}>"
