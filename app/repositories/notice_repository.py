from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import Notice


class NoticeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_hostel(self, hostel_id: str | None) -> list[Notice]:
        query = select(Notice).order_by(Notice.created_at.desc())
        if hostel_id is None:
            query = query.where(Notice.hostel_id.is_(None))
        else:
            query = query.where(or_(Notice.hostel_id == hostel_id, Notice.hostel_id.is_(None)))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, notice: Notice) -> Notice:
        self.session.add(notice)
        await self.session.flush()
        return notice
