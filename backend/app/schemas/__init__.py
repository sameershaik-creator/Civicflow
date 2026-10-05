"""
Pydantic schemas package for CivicFlow.
"""

from app.schemas.user import UserBase, UserCreate, UserResponse
from app.schemas.auth import UserRegister, UserLogin, AuthResponse
from app.schemas.complaint import ComplaintBase, ComplaintDraftUpdate, ComplaintResponse
from app.schemas.notification import NotificationResponse, NotificationUnreadCountResponse
from app.schemas.ai import GeminiComplaintDraft
from app.schemas.location import LocationVerificationResponse

__all__ = [
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserRegister",
    "UserLogin",
    "AuthResponse",
    "ComplaintBase",
    "ComplaintDraftUpdate",
    "ComplaintResponse",
    "NotificationResponse",
    "NotificationUnreadCountResponse",
    "GeminiComplaintDraft",
    "LocationVerificationResponse",
]

