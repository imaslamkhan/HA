from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import Complaint


class ComplaintRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_student(self, student_id: str) -> list[Complaint]:
        result = await self.session.execute(
            select(Complaint).where(Complaint.student_id == student_id).order_by(Complaint.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_hostel(self, hostel_id: str) -> list[Complaint]:
        result = await self.session.execute(
            select(Complaint).where(Complaint.hostel_id == hostel_id).order_by(Complaint.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, complaint: Complaint) -> Complaint:
        self.session.add(complaint)
        await self.session.flush()
        return complaint

    async def get_by_id(self, complaint_id: str) -> Complaint | None:
        result = await self.session.execute(select(Complaint).where(Complaint.id == complaint_id))
        return result.scalar_one_or_none()
