from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, StringConstraints

try:
    import email_validator
    from pydantic import EmailStr
except (ImportError, ModuleNotFoundError):
    # Resilient fallback if email-validator package is not yet installed
    EmailStr = Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_lower=True,
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        )
    ]


from app.models.user import UserRole


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.CITIZEN


class UserCreate(UserBase):
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
