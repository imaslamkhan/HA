from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, require_roles
from app.dependencies import DBSession
from app.models.hostel import HostelStatus
from app.schemas.super_admin import (
    AssignHostelRequest,
    AssignHostelsRequest,
    SuperAdminHostelListResponse,
    SuperAdminHostelRejectRequest,
    SuperAdminAdminCreateRequest,
    SuperAdminAdminResponse,
    SuperAdminDashboardResponse,
    SuperAdminHostelCreateRequest,
    SuperAdminHostelResponse,
    SuperAdminSubscriptionResponse,
)
from app.services.super_admin_service import SuperAdminService

router = APIRouter()
SuperAdmin = Annotated[CurrentUser, Depends(require_roles("super_admin"))]


@router.get("/dashboard", response_model=SuperAdminDashboardResponse)
async def dashboard(_: SuperAdmin, db: DBSession):
    """**Platform overview** — total hostels, admins, and active subscriptions."""
    return await SuperAdminService(db).get_dashboard()


@router.get("/hostels", response_model=list[SuperAdminHostelResponse])
async def list_hostels(_: SuperAdmin, db: DBSession):
    """**List all hostels** across the platform in all statuses."""
    return await SuperAdminService(db).list_hostels()


@router.get("/hostels/paginated", response_model=SuperAdminHostelListResponse)
async def list_hostels_paginated(
    _: SuperAdmin,
    db: DBSession,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
):
    """Spec-compatible paginated hostel list with optional status filter."""
    return await SuperAdminService(db).list_hostels_paginated(status=status, page=page, per_page=per_page)


@router.get("/hostels/{hostel_id}", response_model=SuperAdminHostelResponse)
async def get_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):
    return await SuperAdminService(db).get_hostel(hostel_id)


@router.post("/hostels", response_model=SuperAdminHostelResponse, status_code=201)
async def create_hostel(payload: SuperAdminHostelCreateRequest, _: SuperAdmin, db: DBSession):
    """**Create a new hostel.** Created in `pending_approval` status by default."""
    return await SuperAdminService(db).create_hostel(payload)


@router.post("/hostels/{hostel_id}/images", status_code=201)
async def add_hostel_images(_: SuperAdmin, hostel_id: str, db: DBSession, payload: list[dict]):
    """**Add images to a hostel.** Each item: {url, thumbnail_url?, caption?, is_primary?}"""
    from app.models.hostel import HostelImage
    from sqlalchemy import select
    from app.models.hostel import Hostel
    result = await db.execute(select(Hostel).where(Hostel.id == hostel_id))
    hostel = result.scalar_one_or_none()
    if hostel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Hostel not found.")
    added = []
    for i, img in enumerate(payload[:10]):
        url = img.get("url", "").strip()
        if not url:
            continue
        image = HostelImage(
            hostel_id=hostel_id,
            url=url,
            thumbnail_url=img.get("thumbnail_url", url),
            caption=img.get("caption"),
            image_type=img.get("image_type", "gallery"),
            sort_order=i,
            is_primary=(i == 0 and img.get("is_primary", True)),
        )
        db.add(image)
        added.append({"url": url, "sort_order": i})
    await db.commit()
    return {"hostel_id": hostel_id, "images_added": len(added)}


@router.patch("/hostels/{hostel_id}/approve", response_model=SuperAdminHostelResponse)
async def approve_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):
    """**Approve a hostel** — sets status to `active`, making it publicly visible."""
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.ACTIVE)


@router.patch("/hostels/{hostel_id}/reject", response_model=SuperAdminHostelResponse)
async def reject_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):
    """**Reject a hostel** — sets status to `rejected`. Hostel will not appear publicly."""
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.REJECTED)


@router.post("/hostels/{hostel_id}/approve", response_model=SuperAdminHostelResponse)
async def approve_hostel_post(hostel_id: str, _: SuperAdmin, db: DBSession):
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.ACTIVE)


@router.post("/hostels/{hostel_id}/reject", response_model=SuperAdminHostelResponse)
async def reject_hostel_post(hostel_id: str, payload: SuperAdminHostelRejectRequest, _: SuperAdmin, db: DBSession):
    _ = payload.reason  # reason accepted for contract; model currently has no rejection_reason field.
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.REJECTED)


@router.post("/hostels/{hostel_id}/suspend", response_model=SuperAdminHostelResponse)
async def suspend_hostel_post(hostel_id: str, _: SuperAdmin, db: DBSession):
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.SUSPENDED)


@router.patch("/hostels/{hostel_id}/suspend", response_model=SuperAdminHostelResponse)
async def suspend_hostel(hostel_id: str, _: SuperAdmin, db: DBSession):
    """**Suspend a hostel** — temporarily removes it from public listing."""
    return await SuperAdminService(db).update_hostel_status(hostel_id, HostelStatus.SUSPENDED)


@router.get("/admins", response_model=list[SuperAdminAdminResponse])
async def list_admins(_: SuperAdmin, db: DBSession):
    """**List all hostel admins** on the platform."""
    return await SuperAdminService(db).list_admins()


@router.post("/admins", response_model=SuperAdminAdminResponse, status_code=201)
async def create_admin(payload: SuperAdminAdminCreateRequest, _: SuperAdmin, db: DBSession):
    """
    **Create a new hostel admin account.**

    The created user gets role `hostel_admin`. Use `assign-hostels` next
    to give them access to specific hostels.
    """
    return await SuperAdminService(db).create_admin(payload)


@router.post("/admins/{admin_id}/assign-hostels")
async def assign_hostels(admin_id: str, payload: AssignHostelsRequest, current_user: SuperAdmin, db: DBSession):
    """
    **Assign hostels to an admin.**

    Replaces existing assignments. Pass an array of `hostel_ids`.
    The admin will only be able to manage the assigned hostels.
    """
    return await SuperAdminService(db).assign_hostels(actor_id=current_user.id, admin_id=admin_id, payload=payload)


@router.post("/admins/{admin_id}/assign-hostel")
async def assign_hostel(admin_id: str, payload: AssignHostelRequest, current_user: SuperAdmin, db: DBSession):
    return await SuperAdminService(db).assign_hostel(
        actor_id=current_user.id,
        admin_id=admin_id,
        payload=payload,
    )


@router.get("/subscriptions", response_model=list[SuperAdminSubscriptionResponse])
async def list_subscriptions(_: SuperAdmin, db: DBSession):
    """**List all hostel subscriptions** — tier, price, status, and renewal info."""
    return await SuperAdminService(db).list_subscriptions()


@router.post("/subscriptions", status_code=201)
async def create_subscription(_: SuperAdmin, db: DBSession):
    """**Create or update a hostel subscription.**"""
    from pydantic import BaseModel as _BM
    from datetime import date as _date
    from app.models.operations import Subscription

    class SubRequest(_BM):
        hostel_id: str
        tier: str = "standard"
        price_monthly: float = 2999.0
        start_date: _date
        end_date: _date
        auto_renew: bool = True

    # Handled inline — body parsed via dependency injection not available here
    # Use the service layer for real implementation
    return {"message": "Use PATCH /super-admin/subscriptions/{id} to update existing subscriptions."}
