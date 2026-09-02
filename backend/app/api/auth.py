"""Spec §7: signup creates a profile, an organization, and an owner
membership in one step — "User -> Organization -> Organization membership
-> Recruiter dashboard". Demo-mode only (real mode delegates entirely to
Supabase Auth on the frontend; this router still exposes /me either way)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.persistence.client import get_store
from app.services.auth import (
    CurrentUser,
    create_demo_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""
    organization_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    token: str
    user_id: str
    email: str
    organization_id: str
    organization_name: str


@router.post("/signup", response_model=AuthOut)
def signup(body: SignupIn):
    settings = get_settings()
    if settings.persistence_mode == "real":
        raise HTTPException(
            status_code=400,
            detail="Real mode uses Supabase Auth directly from the frontend — this demo endpoint is disabled.",
        )
    store = get_store()
    if store.get_profile_by_email(body.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    password_hash, salt = hash_password(body.password)
    user_id = store.create_user_with_password(body.email, password_hash, salt, body.display_name)
    org_id = store.create_organization(body.organization_name)
    store.add_org_member(org_id, user_id, role="owner")
    store.append_audit(org_id, "user.signup", "organization", org_id, user_id, {"email": body.email})

    token = create_demo_token(user_id, body.email)
    return AuthOut(token=token, user_id=user_id, email=body.email, organization_id=org_id, organization_name=body.organization_name)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn):
    settings = get_settings()
    if settings.persistence_mode == "real":
        raise HTTPException(status_code=400, detail="Real mode uses Supabase Auth directly from the frontend.")
    store = get_store()
    profile = store.get_profile_by_email(body.email)
    if profile is None or not profile["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(body.password, profile["password_hash"], profile["password_salt"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    orgs = store.list_orgs_for_user(profile["id"])
    if not orgs:
        raise HTTPException(status_code=500, detail="Account has no organization — contact support.")
    org = orgs[0]
    token = create_demo_token(profile["id"], profile["email"])
    return AuthOut(token=token, user_id=profile["id"], email=profile["email"], organization_id=org["id"], organization_name=org["name"])


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    store = get_store()
    orgs = store.list_orgs_for_user(user.user_id)
    return {
        "user_id": user.user_id,
        "email": user.email,
        "organizations": [{"id": o["id"], "name": o["name"]} for o in orgs],
    }
