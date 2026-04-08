from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hostel import Hostel, HostelStatus, HostelType
from app.models.room import Room, RoomType


class HostelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_public(
        self,
        *,
        city: str | None = None,
        hostel_type: str | None = None,
        room_type: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Hostel]:
        query: Select[tuple[Hostel]] = select(Hostel).where(
            Hostel.is_public.is_(True), Hostel.status == HostelStatus.ACTIVE
        )
        if city:
            query = query.where(Hostel.city.ilike(city))
        if hostel_type:
            try:
                query = query.where(Hostel.hostel_type == HostelType(hostel_type.lower()))
            except ValueError:
                pass
        if is_featured is not None:
            query = query.where(Hostel.is_featured.is_(is_featured))
        if room_type or min_price is not None or max_price is not None:
            query = query.join(Room, Room.hostel_id == Hostel.id)
        if room_type:
            try:
                query = query.where(Room.room_type == RoomType(room_type.lower()))
            except ValueError:
                pass
        if min_price is not None:
            query = query.where(Room.monthly_rent >= min_price)
        if max_price is not None:
            query = query.where(Room.monthly_rent <= max_price)
        offset = (page - 1) * page_size
        query = query.distinct().offset(offset).limit(page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_public(
        self,
        *,
        city: str | None = None,
        hostel_type: str | None = None,
        room_type: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        is_featured: bool | None = None,
    ) -> int:
        query = select(Hostel.id).where(
            Hostel.is_public.is_(True), Hostel.status == HostelStatus.ACTIVE
        )
        if city:
            query = query.where(Hostel.city.ilike(city))
        if hostel_type:
            try:
                query = query.where(Hostel.hostel_type == HostelType(hostel_type.lower()))
            except ValueError:
                pass
        if is_featured is not None:
            query = query.where(Hostel.is_featured.is_(is_featured))
        if room_type or min_price is not None or max_price is not None:
            query = query.join(Room, Room.hostel_id == Hostel.id)
        if room_type:
            try:
                query = query.where(Room.room_type == RoomType(room_type.lower()))
            except ValueError:
                pass
        if min_price is not None:
            query = query.where(Room.monthly_rent >= min_price)
        if max_price is not None:
            query = query.where(Room.monthly_rent <= max_price)

        count_query = select(func.count()).select_from(query.distinct().subquery())
        result = await self.session.execute(count_query)
        return int(result.scalar() or 0)

    async def get_by_slug(self, slug: str) -> Hostel | None:
        result = await self.session.execute(select(Hostel).where(Hostel.slug == slug))
        return result.scalar_one_or_none()
