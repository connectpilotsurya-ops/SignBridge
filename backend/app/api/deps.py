"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Path

from app.persistence.client import get_store
from app.services.auth import CurrentUser, get_current_user, require_org_member


def current_user_dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user


class OrgContext:
    def __init__(self, org_id: str, user: CurrentUser):
        self.org_id = org_id
        self.user = user


def org_context_dep(
    x_org_id: str | None = Header(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> OrgContext:
    """Spec §37's endpoints (/api/jobs, /api/resumes/upload, ...) don't carry
    an org id in the path, so it's resolved from the X-Org-Id header (the
    frontend sends this once it knows which org the signed-in user is in)
    — falling back to the user's first/only org, which covers the common
    single-org-per-user demo case without forcing the header on every call.
    Either way, membership is verified before any data is touched."""
    store = get_store()
    org_id = x_org_id
    if not org_id:
        orgs = store.list_orgs_for_user(user.user_id)
        if not orgs:
            raise HTTPException(status_code=403, detail="User belongs to no organization.")
        org_id = orgs[0]["id"]
    require_org_member(org_id, user)
    return OrgContext(org_id=org_id, user=user)


def org_member_dep(org_id: str = Path(...), user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    require_org_member(org_id, user)
    return user


def get_job_or_404(org_id: str, job_id: str):
    store = get_store()
    job = store.get_job(org_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def get_application_or_404(org_id: str, application_id: str):
    store = get_store()
    application = store.get_application(org_id, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application
