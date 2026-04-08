from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import MessMenu, MessMenuItem


class MessMenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_hostel(self, hostel_id: str) -> list[MessMenu]:
        result = await self.session.execute(
            select(MessMenu).where(MessMenu.hostel_id == hostel_id).order_by(MessMenu.week_start_date.desc())
        )
        return list(result.scalars().all())

    async def list_by_hostel_with_items(self, hostel_id: str) -> list[MessMenu]:
        result = await self.session.execute(
            select(MessMenu)
            .options(selectinload(MessMenu.items))
            .where(MessMenu.hostel_id == hostel_id)
            .order_by(MessMenu.week_start_date.desc())
        )
        return list(result.scalars().all())

    async def create_menu(self, menu: MessMenu) -> MessMenu:
        self.session.add(menu)
        await self.session.flush()
        return menu

    async def create_item(self, item: MessMenuItem) -> MessMenuItem:
        self.session.add(item)
        await self.session.flush()
        return item
