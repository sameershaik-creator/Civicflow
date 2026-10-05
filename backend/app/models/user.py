import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, Enum):
    CITIZEN = "citizen"
    ADMIN = "admin"


class User(Base):
    """
    User entity representing citizens and municipal administrators.
    Passwords are never stored as plaintext; only password_hash is persisted.
    """
    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    name = Column(String(128), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        default=UserRole.CITIZEN.value
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # ORM Relationships
    complaints = relationship(
        "Complaint",
        back_populates="user",
        lazy="select"
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        lazy="select"
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
