from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.visitor_repository import VisitorRepository


class VisitorService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = VisitorRepository(session)

    async def list_bookings(self, visitor_id: str):
        return await self.repository.list_bookings(visitor_id)
