from calendar import monthrange
from datetime import date

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import AttendanceRecord
from app.models.student import Student
from app.models.user import User


class AttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_hostel_ids(self, hostel_ids: list[str]) -> list[AttendanceRecord]:
        if not hostel_ids:
            return []
        result = await self.session.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.hostel_id.in_(hostel_ids))
            .order_by(AttendanceRecord.date.desc(), AttendanceRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_student_by_id(self, student_id: str) -> Student | None:
        result = await self.session.execute(select(Student).where(Student.id == student_id))
        return result.scalar_one_or_none()

    async def get_by_student_and_date(self, *, student_id: str, date) -> AttendanceRecord | None:
        result = await self.session.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.date == date,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, record: AttendanceRecord) -> AttendanceRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def monthly_summary_for_hostel(
        self, hostel_id: str, year: int, month: int
    ) -> list[tuple[str, str, str, int, int]]:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        present_expr = func.coalesce(
            func.sum(case((AttendanceRecord.status == "present", 1), else_=0)),
            0,
        )
        result = await self.session.execute(
            select(
                Student.id,
                Student.student_number,
                User.full_name,
                func.count(AttendanceRecord.id).label("total_marked"),
                present_expr.label("present_count"),
            )
            .join(User, User.id == Student.user_id)
            .outerjoin(
                AttendanceRecord,
                and_(
                    AttendanceRecord.student_id == Student.id,
                    AttendanceRecord.date >= start,
                    AttendanceRecord.date <= end,
                ),
            )
            .where(Student.hostel_id == hostel_id)
            .group_by(Student.id, Student.student_number, User.full_name)
            .order_by(User.full_name)
        )
        rows = []
        for sid, snum, fname, total_marked, present_count in result.all():
            rows.append(
                (
                    str(sid),
                    snum,
                    fname or "",
                    int(present_count or 0),
                    int(total_marked or 0),
                )
            )
        return rows
