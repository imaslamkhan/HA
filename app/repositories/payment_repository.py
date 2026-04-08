from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.student import Student


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_student_by_user(self, user_id: str) -> Student | None:
        result = await self.session.execute(select(Student).where(Student.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_by_student(self, student_id: str) -> list[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.student_id == student_id).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_hostel(self, hostel_id: str) -> list[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.hostel_id == hostel_id).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())
