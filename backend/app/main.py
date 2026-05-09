"""
Aurora Gracewood — FastAPI backend skeleton.

Phase C scaffolding (2026-05-06). Endpoints below are routed and accept
the right schemas, but most return STUB responses. They establish the API
shape so the frontend can be migrated from localStorage to real fetch()
calls one endpoint at a time.

Run for local dev:
    cd backend
    pip install -r requirements.txt
    cp .env.example .env  # then fill values
    uvicorn app.main:app --reload --port 8000

Frontend integration (later):
    Replace `auth.js` localStorage operations with fetch() calls against
    these endpoints. Keep the AGAuth public surface identical so consumers
    (awards forms, profile editor, auth chip) don't change.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from . import models


app = FastAPI(
    title="Aurora Gracewood API",
    version="0.1.0-skeleton",
    description="Backend API for Aurora Gracewood account, profile, awards submission, and community choice systems.",
)


# CORS — allow frontend origins from .env (CORS_ORIGINS comma-separated).
_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://127.0.0.1:9333,http://localhost:9333"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/signin", auto_error=False)


def get_current_profile(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[models.ProfileOut]:
    """Stub auth dependency. Phase C+ replaces with real JWT decode + DB lookup.
    Returns None when not authenticated (callers decide whether to 401)."""
    if not token:
        return None
    # TODO: decode JWT, look up profile in DB, return.
    return None


def require_profile(token: Optional[str] = Depends(oauth2_scheme)) -> models.ProfileOut:
    """Auth dependency that 401s if no valid token."""
    profile = get_current_profile(token)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return profile


# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "aurora-gracewood-api", "version": app.version}


# -----------------------------------------------------------------------------
# Auth endpoints — STUB. Phase C+ wires real DB + password hashing + JWT.
# -----------------------------------------------------------------------------
@app.post("/api/auth/signup", response_model=models.TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: models.ProfileCreate):
    """Stub — accepts a signup payload, returns a stub token + profile.
    Phase C+ will: hash password (passlib), insert User row, issue JWT.

    Role assignment: if the email matches INITIAL_SUPERUSER_EMAIL env var,
    this user is the Superuser. Mirrors /account/auth.js stub behavior."""
    now = datetime.now(timezone.utc)
    superuser_email = (os.environ.get("INITIAL_SUPERUSER_EMAIL", "") or "").lower()
    role: models.Role = "superuser" if str(payload.email).lower() == superuser_email else "client"
    profile = models.ProfileOut(
        name=payload.name,
        email=payload.email,
        public_slug=payload.public_slug or _slug_from(payload.name, payload.email),
        public_bio=payload.public_bio or "",
        avatar_url=payload.avatar_url or "",
        marketing_share=payload.marketing_share,
        role=role,
        created_at=now,
        updated_at=now,
    )
    # TODO: persist to DB; check email uniqueness.
    return models.TokenResponse(access_token="stub-token", profile=profile)


@app.post("/api/auth/signin", response_model=models.TokenResponse)
def signin(req: models.SignInRequest):
    """Stub — accepts email + password, returns stub token + profile.
    Phase C+ will verify password against hashed value, issue real JWT."""
    # TODO: look up by email, verify password, issue token.
    raise HTTPException(status_code=501, detail="signin not implemented in skeleton")


@app.post("/api/auth/signout")
def signout(profile: models.ProfileOut = Depends(require_profile)):
    """Stub — invalidates the user's session. Phase C+ may revoke JWT
    via blacklist or short-TTL strategy."""
    return {"ok": True}


# -----------------------------------------------------------------------------
# Profile endpoints
# -----------------------------------------------------------------------------
@app.get("/api/profile", response_model=models.ProfileOut)
def get_profile(profile: models.ProfileOut = Depends(require_profile)):
    """Returns the current user's full profile."""
    return profile


@app.patch("/api/profile", response_model=models.ProfileOut)
def update_profile(
    patch: models.ProfileUpdate,
    profile: models.ProfileOut = Depends(require_profile),
):
    """Stub — merges patch into the user's profile, stamps updated_at."""
    # TODO: persist to DB.
    raise HTTPException(status_code=501, detail="update_profile not implemented in skeleton")


@app.delete("/api/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(profile: models.ProfileOut = Depends(require_profile)):
    """Stub — removes the user's account + cascades to submissions."""
    # TODO: hard-delete or soft-delete; cascade rules.
    raise HTTPException(status_code=501, detail="delete_account not implemented in skeleton")


# -----------------------------------------------------------------------------
# Public profile lookup
# -----------------------------------------------------------------------------
@app.get("/api/clients/{slug}", response_model=models.ProfileOut)
def get_public_profile(slug: str):
    """Public partial profile by slug. Returns name, bio, avatar, role —
    NOT email or marketing_share. Used by /awards/clients/<slug> page."""
    # TODO: look up by slug; return only public-safe fields.
    raise HTTPException(status_code=404, detail="profile not found")


# -----------------------------------------------------------------------------
# Submission endpoints
# -----------------------------------------------------------------------------
@app.post("/api/submissions", response_model=models.SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: models.SubmissionCreate,
    profile: models.ProfileOut = Depends(require_profile),
):
    """Stub — accepts a submission, attaches to current user, returns record."""
    # TODO: persist + trigger payment intent + enqueue review.
    raise HTTPException(status_code=501, detail="create_submission not implemented in skeleton")


@app.get("/api/submissions/mine", response_model=List[models.SubmissionOut])
def list_my_submissions(profile: models.ProfileOut = Depends(require_profile)):
    """Returns the current user's submissions. Used by 'My Submissions' in profile UI."""
    # TODO: query DB.
    return []


# -----------------------------------------------------------------------------
# Community Choice endpoints (Phase 5 — placeholder routes)
# -----------------------------------------------------------------------------
@app.get("/api/community-choice/leaderboard")
def cc_leaderboard():
    """Public leaderboard. Returns top-N brands ranked by point tally."""
    return {"cycle": _current_cycle_id(), "leaderboard": []}


@app.post("/api/community-choice/vote")
def cc_vote(brand_slug: str, profile: models.ProfileOut = Depends(require_profile)):
    """Cast a social-amplification vote (1 point) for a brand. Idempotent on
    (account_id, brand_slug, cycle_id)."""
    # TODO: enforce unique constraint; record vote.
    raise HTTPException(status_code=501, detail="cc_vote not implemented in skeleton")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _slug_from(name: str, email: str) -> str:
    """Mirror the frontend's makeSlug() behavior for consistency."""
    import re
    base = (name or email.split("@")[0] or "user").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:30]
    return base or "user"


def _current_cycle_id() -> str:
    """Returns a cycle identifier for the current calendar year.
    Future: support quarterly or monthly cycles by including a sub-key."""
    return str(datetime.now(timezone.utc).year)
