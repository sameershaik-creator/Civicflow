"""
Authentication and Authorization Dependencies for CivicFlow.

Provides:
- Database session dependency (get_db).
- User authentication dependency (get_current_user).
- Role-based authorization dependency (require_admin).
- Resource ownership helper for row-level access control (check_resource_ownership).
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.services import auth_service

# Bearer token extractor without automatic error so we can format standard RFC-compliant 401 errors
security = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts and validates the JWT Bearer token from request headers.
    Loads the user directly from the database using the token subject.
    Never trusts identity or roles supplied from request bodies or headers.

    Raises:
        HTTPException 401: If token is missing, expired, invalid, or user not found.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials

    try:
        payload = auth_service.decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except auth_service.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (auth_service.InvalidTokenError, auth_service.PyJWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Enforces administrator role-based access control (RBAC).

    Requires:
        An authenticated user with role == UserRole.ADMIN.

    Raises:
        HTTPException 401: If unauthenticated (handled by get_current_user).
        HTTPException 403: If authenticated user is NOT an administrator.
    """
    is_admin = (
        current_user.role == UserRole.ADMIN.value or
        current_user.role == UserRole.ADMIN
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges required"
        )
    return current_user


def check_resource_ownership(
    resource_owner_id: str,
    current_user: User
) -> bool:
    """
    Reusable authorization foundation for row-level resource ownership:
    - Administrators have universal access to all civic resources.
    - Citizens have access ONLY to resources where resource.user_id == current_user.id.

    Raises:
        HTTPException 403: If the citizen attempts to access another user's resource.
    """
    is_admin = (
        current_user.role == UserRole.ADMIN.value or
        current_user.role == UserRole.ADMIN
    )
    if is_admin:
        return True

    if str(resource_owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access or modify this resource"
        )
    return True
