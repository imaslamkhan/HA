from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hostel import AdminHostelMapping, Hostel, HostelStatus, HostelType
from app.models.operations import Subscription
from app.models.user import User, UserRole


class SuperAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_hostels(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Hostel))
        return int(result.scalar_one() or 0)

    async def count_admins(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.HOSTEL_ADMIN)
        )
        return int(result.scalar_one() or 0)

    async def count_subscriptions(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Subscription))
        return int(result.scalar_one() or 0)

    async def list_hostels(self) -> list[Hostel]:
        result = await self.session.execute(select(Hostel).order_by(Hostel.created_at.desc()))
        return list(result.scalars().all())

    async def list_hostels_paginated(
        self, *, status: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[list[Hostel], int]:
        query = select(Hostel)
        count_query = select(func.count()).select_from(Hostel)
        if status:
            try:
                status_enum = HostelStatus(status)
                query = query.where(Hostel.status == status_enum)
                count_query = count_query.where(Hostel.status == status_enum)
            except ValueError:
                pass
        query = query.order_by(Hostel.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        hostels_result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return list(hostels_result.scalars().all()), int(total_result.scalar_one() or 0)

    async def create_hostel(self, hostel: Hostel) -> Hostel:
        self.session.add(hostel)
        await self.session.flush()
        return hostel

    async def get_hostel_by_id(self, hostel_id: str) -> Hostel | None:
        result = await self.session.execute(select(Hostel).where(Hostel.id == hostel_id))
        return result.scalar_one_or_none()

    async def list_admins(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.role == UserRole.HOSTEL_ADMIN).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_admin(self, admin: User) -> User:
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def get_admin_by_id(self, admin_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == admin_id, User.role == UserRole.HOSTEL_ADMIN)
        )
        return result.scalar_one_or_none()

    async def replace_admin_hostels(self, admin_id: str, hostel_ids: list[str], assigned_by: str) -> None:
        await self.session.execute(delete(AdminHostelMapping).where(AdminHostelMapping.admin_id == admin_id))
        for index, hostel_id in enumerate(hostel_ids):
            self.session.add(
                AdminHostelMapping(
                    admin_id=admin_id,
                    hostel_id=hostel_id,
                    is_primary=index == 0,
                    assigned_by=assigned_by,
                )
            )
        await self.session.flush()

    async def list_subscriptions(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription).order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())
