from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hostel import SupervisorHostelMapping
from app.models.student import Student


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_student_by_user(self, user_id: str) -> Student | None:
        result = await self.session.execute(select(Student).where(Student.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_supervisor_hostel_ids(self, supervisor_id: str) -> list[str]:
        result = await self.session.execute(
            select(SupervisorHostelMapping.hostel_id).where(
                SupervisorHostelMapping.supervisor_id == supervisor_id
            )
        )
        return [str(hostel_id) for hostel_id in result.scalars().all()]
