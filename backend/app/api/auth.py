"""
Authentication API Endpoints for CivicFlow.

Implements the frozen Phase 0 API contract:
- POST /api/v1/auth/register (Public citizen registration, always citizen role)
- POST /api/v1/auth/login    (Email/password verification, JWT issuance)
- GET  /api/v1/auth/me       (Authenticated user identity extraction)
- GET  /api/v1/auth/admin-only (Minimal RBAC dependency test endpoint)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import UserRegister, UserLogin, AuthResponse
from app.schemas.user import UserResponse
from app.services import auth_service
from app.api.deps import get_current_user, require_admin

logger = logging.getLogger("civicflow.api.auth")

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen",
    description="Registers a new citizen with safe password hashing. Public registrations are strictly created with the 'citizen' role."
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a citizen user:
    1. Validates schema.
    2. Enforces lowercased, stripped email.
    3. Verifies email uniqueness (409 Conflict if duplicate).
    4. Hashes password securely via bcrypt (plaintext password is never stored).
    5. Always sets role to 'citizen' (rejects or ignores any role supplied in payload).
    6. Returns safe UserResponse without password_hash.
    """
    try:
        user = auth_service.register_user(
            db=db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    # Issue initial access token upon registration
    token = auth_service.create_access_token(
        subject=user.id,
        role=user.role
    )

    user_resp = UserResponse.model_validate(user)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates via email and password, returning a signed JWT access token and safe user profile."
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates a user:
    1. Normalizes email.
    2. Verifies password against stored bcrypt hash.
    3. Rejects invalid credentials with generic 401 (does not leak email existence).
    4. Issues signed JWT access token.
    5. Returns safe user data (password_hash is never serialized).
    """
    user = auth_service.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_service.create_access_token(
        subject=user.id,
        role=user.role
    )

    user_resp = UserResponse.model_validate(user)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
    description="Returns the currently authenticated user's profile using the Bearer token."
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Returns current authenticated user identity:
    1. Validates JWT signature and expiration.
    2. Retrieves user record directly from database.
    3. Serializes only safe fields (id, name, email, role, created_at).
    """
    return UserResponse.model_validate(current_user)


@router.get(
    "/admin-only",
    status_code=status.HTTP_200_OK,
    summary="RBAC verification endpoint (Admin only)",
    description="Minimal RBAC test endpoint requiring administrator privileges. Returns 403 for citizens and 401 for unauthenticated requests."
)
def admin_only_test(
    current_admin: User = Depends(require_admin)
):
    """
    Protected endpoint to test role-based access control:
    - 401 if unauthenticated
    - 403 if authenticated citizen
    - 200 if authenticated admin
    """
    return {
        "status": "ok",
        "message": "Admin authorization verified",
        "admin_id": current_admin.id,
        "admin_email": current_admin.email,
        "role": current_admin.role,
    }
