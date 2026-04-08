from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PaymentRepository(session)

    async def list_student_payments(self, *, user_id: str):
        student = await self.repository.get_student_by_user(user_id)
        if student is None:
            return []
        return await self.repository.list_by_student(str(student.id))

    async def list_admin_payments(self, *, hostel_id: str):
        return await self.repository.list_by_hostel(hostel_id)
