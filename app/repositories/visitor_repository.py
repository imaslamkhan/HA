from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking


class VisitorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_bookings(self, visitor_id: str) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(Booking.visitor_id == visitor_id).order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())
