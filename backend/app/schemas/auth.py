from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.schemas.user import UserResponse, EmailStr



class UserRegister(BaseModel):
    """
    Schema for citizen registration.
    Public registration can NEVER elevate privileges or specify roles.
    Any 'role', 'admin', or 'permissions' submitted is strictly rejected or ignored.
    """
    name: str = Field(..., min_length=1, max_length=128, description="User full name")
    email: EmailStr = Field(..., description="User unique email address")
    password: str = Field(..., min_length=6, max_length=128, description="Secure password")
    role: Optional[str] = Field(None, description="Forbidden/ignored on public register - always defaults to citizen")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserLogin(BaseModel):
    """Schema for authentication login."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Password")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AuthResponse(BaseModel):
    """
    Authentication response returning JWT access token and safe user details.
    Never exposes password or password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    # Top-level mirrors for client convenience
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
