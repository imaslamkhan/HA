from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import MaintenanceRequest


class MaintenanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_hostel(self, hostel_id: str) -> list[MaintenanceRequest]:
        result = await self.session.execute(
            select(MaintenanceRequest)
            .where(MaintenanceRequest.hostel_id == hostel_id)
            .order_by(MaintenanceRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, request: MaintenanceRequest) -> MaintenanceRequest:
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_by_id(self, request_id: str) -> MaintenanceRequest | None:
        result = await self.session.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        return result.scalar_one_or_none()
