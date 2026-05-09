"""
Aurora Gracewood — Pydantic models matching the frontend AGAuth profile schema.

The shape mirrors what `account/auth.js` writes to localStorage today, so the
swap-in path from stub to real backend is mechanical: the JSON the frontend
already produces becomes the JSON the API consumes.

When SQLAlchemy ORM models are added (Phase C+), they will share the same
field names so Pydantic <-> ORM conversion stays trivial.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


Role = Literal["client", "agent", "regular_admin", "superuser"]


class ProfileBase(BaseModel):
    """Fields a user can edit themselves via /account/."""
    name: str = Field(..., min_length=1, max_length=120)
    public_slug: Optional[str] = Field(default=None, pattern=r"^[a-z0-9-]+$", max_length=30)
    public_bio: Optional[str] = Field(default="", max_length=280)
    avatar_url: Optional[str] = Field(default="")
    marketing_share: bool = False


class ProfileCreate(ProfileBase):
    """Inbound payload at signup. Email is set here, never editable later."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class ProfileUpdate(BaseModel):
    """Inbound payload from /account/ profile editor. All fields optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    public_slug: Optional[str] = Field(default=None, pattern=r"^[a-z0-9-]+$", max_length=30)
    public_bio: Optional[str] = Field(default=None, max_length=280)
    avatar_url: Optional[str] = None
    marketing_share: Optional[bool] = None


class ProfileOut(ProfileBase):
    """Outbound payload — what /api/profile returns. Never includes password."""
    email: EmailStr
    role: Role = "client"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    profile: ProfileOut


class SubmissionCreate(BaseModel):
    """Inbound payload from any awards submission form. Schema is loose
    because each submission type has different fields — backend stores the
    raw form data and a few attribution fields."""
    submission_type: str
    payload: dict
    # Frontend includes these in payload via underscore-prefixed keys, but
    # we extract them server-side as first-class attribution fields.

    model_config = ConfigDict(extra="allow")


class SubmissionOut(BaseModel):
    id: str
    submission_type: str
    submitter_email: EmailStr
    submitter_name: str
    public_slug: Optional[str]
    role_at_submission: Role
    payload: dict
    submitted_at: datetime
    status: Literal["pending", "in_review", "finalist", "honoree", "winner", "rejected"] = "pending"

    model_config = ConfigDict(from_attributes=True)


class CommunityChoicePoint(BaseModel):
    """Each row in the points ledger for Community Choice. One vote = one row."""
    brand_slug: str
    cycle_id: str
    points: int
    source: Literal["bundled_at_cat_sub", "direct_cc_sub", "social_vote", "public_mention"]
    source_account: Optional[str] = None  # Platform account ID for social votes
    awarded_at: datetime
