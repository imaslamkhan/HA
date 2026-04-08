from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.operations import AttendanceRecord, MessMenu, Notice
from app.models.student import Student
from app.models.user import User


class StudentReadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_student_by_user(self, user_id: str) -> Student | None:
        result = await self.session.execute(select(Student).where(Student.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_attendance(self, student_id: str) -> list[AttendanceRecord]:
        result = await self.session.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id == student_id)
            .order_by(AttendanceRecord.date.desc())
        )
        return list(result.scalars().all())

    async def list_bookings(self, booking_id: str | None) -> list[Booking]:
        if not booking_id:
            return []
        result = await self.session.execute(
            select(Booking).where(Booking.id == booking_id).order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_bookings_by_visitor(self, user_id: str) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(Booking.visitor_id == user_id).order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_notices(self, hostel_id: str) -> list[Notice]:
        result = await self.session.execute(
            select(Notice)
            .where(
                or_(Notice.hostel_id == hostel_id, Notice.hostel_id.is_(None)),
                Notice.is_published.is_(True),
            )
            .order_by(Notice.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_mess_menus(self, hostel_id: str) -> list[MessMenu]:
        result = await self.session.execute(
            select(MessMenu)
            .options(selectinload(MessMenu.items))
            .where(MessMenu.hostel_id == hostel_id, MessMenu.is_active.is_(True))
            .order_by(MessMenu.week_start_date.desc())
        )
        return list(result.scalars().all())
