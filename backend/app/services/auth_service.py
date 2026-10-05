"""
CivicFlow Authentication Service.

Handles:
- Secure password hashing and verification using standard bcrypt.
- JWT creation and decoding with configurable expiration and secret key.
- Safe user registration (enforcing default citizen role).
- User authentication and lookup.
- Admin user seeding (for development and testing only).
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.models.user import User, UserRole

logger = logging.getLogger("civicflow.auth")

# ---------------------------------------------------------------------------
# Password Hashing Implementation
# ---------------------------------------------------------------------------
# Standard secure password hashing using passlib / bcrypt.
# No custom hashing, MD5, SHA1, or plain algorithms used.
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        import types
        bcrypt.__about__ = types.SimpleNamespace(__version__=getattr(bcrypt, "__version__", "4.0.0"))
    from passlib.context import CryptContext
    # Validate bcrypt context initialization
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Quick probe to ensure compatibility
    _ctx.hash("probe")
    pwd_context = _ctx


    def hash_password(password: str) -> str:
        """Hash a plaintext password securely using standard bcrypt."""
        if not password:
            raise ValueError("Password cannot be empty")
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against the stored bcrypt hash."""
        if not plain_password or not hashed_password:
            return False
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as exc:
            logger.warning("Password verification error: %s", exc)
            return False

except Exception:
    import bcrypt

    def hash_password(password: str) -> str:
        """Hash a plaintext password securely using direct bcrypt."""
        if not password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against the stored bcrypt hash."""
        if not plain_password or not hashed_password:
            return False
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception as exc:
            logger.warning("Bcrypt verification error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# JWT Token Handling
# ---------------------------------------------------------------------------
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError


def create_access_token(
    subject: str,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed JWT access token.
    Token contains subject (user id), expiration, and issued-at timestamp.
    Passwords and password hashes are NEVER included in tokens.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if role:
        payload["role"] = str(role)

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a signed JWT access token.
    Raises ExpiredSignatureError if expired, InvalidTokenError if invalid.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


# ---------------------------------------------------------------------------
# User Data Operations
# ---------------------------------------------------------------------------
def normalize_email(email: str) -> str:
    """Normalize email addresses consistently (lowercase and stripped)."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Look up a user by normalized email."""
    normalized = normalize_email(email)
    return db.query(User).filter(User.email == normalized).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Look up a user by unique identifier."""
    return db.query(User).filter(User.id == str(user_id)).first()


def register_user(
    db: Session,
    name: str,
    email: str,
    password: str
) -> User:
    """
    Register a new citizen in CivicFlow.
    
    Security Guarantees:
    - Normalizes email.
    - Hashes password securely (plaintext password is NEVER persisted).
    - Public registration strictly enforces role = UserRole.CITIZEN.
    - Cannot create admin or elevate privileges.
    """
    normalized = normalize_email(email)
    
    existing = get_user_by_email(db, normalized)
    if existing:
        raise ValueError("Email already registered")

    hashed_pw = hash_password(password)

    new_user = User(
        id=str(uuid.uuid4()),
        name=name.strip(),
        email=normalized,
        password_hash=hashed_pw,
        role=UserRole.CITIZEN.value,  # Strict backend enforcement: always citizen
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(
    db: Session,
    email: str,
    password: str
) -> Optional[User]:
    """
    Authenticate user using email and password.
    Returns User if valid, None if credentials do not match.
    Does not leak whether the email exists.
    """
    normalized = normalize_email(email)
    user = get_user_by_email(db, normalized)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_admin_user(
    db: Session,
    name: str,
    email: str,
    password: str
) -> User:
    """
    DEVELOPMENT / TESTING SEED HELPER ONLY.
    Creates an admin user with explicit administrative role.
    This function is never exposed to public HTTP registration.
    """
    normalized = normalize_email(email)
    existing = get_user_by_email(db, normalized)
    if existing:
        raise ValueError("Admin user already exists with this email")

    hashed_pw = hash_password(password)

    admin_user = User(
        id=str(uuid.uuid4()),
        name=name.strip(),
        email=normalized,
        password_hash=hashed_pw,
        role=UserRole.ADMIN.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user
