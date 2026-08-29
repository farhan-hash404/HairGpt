from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)
    fitzpatrick_self: int | None = Field(default=None, ge=1, le=6)
    year_of_birth: int | None = Field(default=None, ge=1900, le=2025)
    sex: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: str
    fitzpatrick_self: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileIn(BaseModel):
    """Optional self-reported profile.

    Collected solely so model performance can be reported per subgroup, which
    the fairness evaluation requires. Never used for identification.
    """

    display_name: str | None = Field(default=None, max_length=120)
    fitzpatrick_self: int | None = Field(default=None, ge=1, le=6)
    year_of_birth: int | None = Field(default=None, ge=1900, le=2026)
    sex: str | None = Field(default=None, max_length=16)


class ConsentIn(BaseModel):
    purpose: str
    granted: bool
    policy_version: str = "1.0"


class ConsentOut(BaseModel):
    purpose: str
    granted: bool
    policy_version: str

    model_config = {"from_attributes": True}
