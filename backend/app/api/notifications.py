"""
Citizen In-App Notification API Router (Phase 10).

Provides:
- GET /api/v1/notifications: List notifications belonging to authenticated citizen.
- GET /api/v1/notifications/unread-count: Return count of unread notifications for authenticated citizen.
- GET /api/v1/notifications/{notification_id}: Retrieve single notification with row-level ownership.
- PATCH /api/v1/notifications/{notification_id}/read: Mark notification as read (idempotent, ownership-protected).

Security Guarantees:
- Enforces JWT authentication on all endpoints (401 Unauthorized for missing/invalid tokens).
- Strictly scopes queries to current_user.id (prevents cross-user data leakage).
- Enforces row-level ownership checks (403 Forbidden if a citizen attempts to view/modify another citizen's notification).
- Immutability of notification content: Client cannot forge, inject, or tamper with user_id, complaint_id, title, message, or created_at.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.notification import NotificationResponse, NotificationUnreadCountResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List citizen notifications",
    description="Retrieves persistent in-app notifications belonging exclusively to the authenticated user, ordered newest first."
)
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List citizen in-app notifications:
    - 401 if unauthenticated.
    - Scoped strictly to current_user.id.
    - Ordered by created_at DESC (newest first).
    - Returns empty list [] if no notifications exist (truthful empty state).
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return notifications


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get count of unread citizen notifications",
    description="Returns the exact count of unread notifications belonging to the authenticated citizen."
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unread notification count:
    - 401 if unauthenticated.
    - Scoped strictly to current_user.id where is_read == False.
    - Returns real database count; never hardcoded.
    """
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False)
        )
        .count()
    )
    return NotificationUnreadCountResponse(unread_count=count)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single notification detail",
    description="Retrieves a single notification by ID, enforcing strict row-level ownership."
)
def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve single notification:
    - 401 if unauthenticated.
    - 404 if notification not found.
    - 403 if notification does not belong to authenticated citizen.
    - 200 with notification details if authorized.
    """
    notification = db.query(Notification).filter(Notification.id == str(notification_id)).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Enforce row-level ownership: only the notification owner can view it
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this notification"
        )

    return notification


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Updates the is_read status of a notification to true. Safe and idempotent."
)
def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark notification read:
    - 401 if unauthenticated.
    - 404 if notification not found.
    - 403 if notification does not belong to authenticated citizen.
    - Sets is_read = True.
    - Immutability: title, message, user_id, complaint_id, and created_at cannot be altered.
    - Idempotent: marking already-read notification as read succeeds without side effects.
    - Returns updated NotificationResponse.
    """
    notification = db.query(Notification).filter(Notification.id == str(notification_id)).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Enforce row-level ownership: only the notification owner can mark it read
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to modify this notification"
        )

    if not notification.is_read:
        notification.is_read = True
        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
        except Exception as e:
            db.rollback()
            logger.error("Failed to mark notification %s as read: %s", notification_id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while marking notification as read."
            )

    return notification
