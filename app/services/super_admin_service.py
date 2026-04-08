from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.hostel import Hostel, HostelStatus, HostelType
from app.models.payment import Payment
from app.models.student import Student
from app.models.user import User, UserRole
from app.repositories.super_admin_repository import SuperAdminRepository
from app.schemas.super_admin import (
    AssignHostelRequest,
    AssignHostelsRequest,
    SuperAdminHostelListResponse,
    SuperAdminAdminCreateRequest,
    SuperAdminDashboardResponse,
    SuperAdminHostelCreateRequest,
)


class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SuperAdminRepository(session)

    async def get_dashboard(self) -> SuperAdminDashboardResponse:
        hostels = await self.repository.count_hostels()
        admins = await self.repository.count_admins()
        subscriptions = await self.repository.count_subscriptions()
        pending_result = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.PENDING_APPROVAL)
        )
        active_result = await self.session.execute(
            select(func.count()).select_from(Hostel).where(Hostel.status == HostelStatus.ACTIVE)
        )
        students_result = await self.session.execute(select(func.count()).select_from(Student))
        revenue_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.status == "captured",
                func.date_trunc("month", Payment.created_at) == func.date_trunc("month", func.now()),
            )
        )
        pending = int(pending_result.scalar_one() or 0)
        active = int(active_result.scalar_one() or 0)
        total_students = int(students_result.scalar_one() or 0)
        revenue_month = float(revenue_result.scalar_one() or 0)
        return SuperAdminDashboardResponse(
            total_hostels=hostels,
            pending_approval_count=pending,
            active_hostels=active,
            total_students=total_students,
            total_revenue_month=revenue_month,
            hostels=hostels,
            admins=admins,
            subscriptions=subscriptions,
        )

    async def list_hostels(self):
        return await self.repository.list_hostels()

    async def list_hostels_paginated(self, *, status: str | None = None, page: int = 1, per_page: int = 20):
        items, total = await self.repository.list_hostels_paginated(status=status, page=page, per_page=per_page)
        return SuperAdminHostelListResponse(items=items, total=total, page=page, per_page=per_page)

    async def get_hostel(self, hostel_id: str):
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
        return hostel

    async def create_hostel(self, payload: SuperAdminHostelCreateRequest):
        hostel = Hostel(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            hostel_type=HostelType(payload.hostel_type),
            status=HostelStatus.PENDING_APPROVAL,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            pincode=payload.pincode,
            latitude=payload.latitude,
            longitude=payload.longitude,
            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            is_featured=payload.is_featured,
            is_public=payload.is_public,
            rules_and_regulations=payload.rules_and_regulations,
        )
        hostel = await self.repository.create_hostel(hostel)
        await self.session.commit()
        await self.session.refresh(hostel)
        return hostel

    async def update_hostel_status(self, hostel_id: str, status_value: HostelStatus):
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
        hostel.status = status_value
        await self.session.commit()
        await self.session.refresh(hostel)
        return hostel

    async def list_admins(self):
        return await self.repository.list_admins()

    async def create_admin(self, payload: SuperAdminAdminCreateRequest):
        admin = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.HOSTEL_ADMIN,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        admin = await self.repository.create_admin(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin

    async def assign_hostels(self, actor_id: str, admin_id: str, payload: AssignHostelsRequest):
        admin = await self.repository.get_admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")
        await self.repository.replace_admin_hostels(admin_id=admin_id, hostel_ids=payload.hostel_ids, assigned_by=actor_id)
        await self.session.commit()
        return {"admin_id": admin_id, "hostel_ids": payload.hostel_ids}

    async def assign_hostel(self, actor_id: str, admin_id: str, payload: AssignHostelRequest):
        admin = await self.repository.get_admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")
        current = await self.repository.list_hostels()
        _ = current  # keep repository usage explicit for consistency
        # Preserve existing mappings and upsert one hostel with requested primary flag.
        from app.models.hostel import AdminHostelMapping

        result = await self.session.execute(
            select(AdminHostelMapping).where(AdminHostelMapping.admin_id == admin_id)
        )
        mappings = list(result.scalars().all())
        if payload.is_primary:
            for m in mappings:
                m.is_primary = False
        existing = next((m for m in mappings if str(m.hostel_id) == payload.hostel_id), None)
        if existing:
            existing.is_primary = payload.is_primary or existing.is_primary
        else:
            self.session.add(
                AdminHostelMapping(
                    admin_id=admin_id,
                    hostel_id=payload.hostel_id,
                    is_primary=payload.is_primary or len(mappings) == 0,
                    assigned_by=actor_id,
                )
            )
        await self.session.commit()
        return {"admin_id": admin_id, "hostel_id": payload.hostel_id, "is_primary": payload.is_primary}

    async def list_subscriptions(self):
        return await self.repository.list_subscriptions()
