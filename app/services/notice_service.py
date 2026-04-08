from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import Notice, NoticeRead
from app.models.student import Student
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.notice_repository import NoticeRepository
from app.schemas.notice import NoticeCreateRequest


class NoticeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = NoticeRepository(session)
        self.assignments = AssignmentRepository(session)

    async def list_admin_notices(self, *, hostel_id: str):
        return await self.repository.list_by_hostel(hostel_id)

    async def list_notice_read_stats(self, *, hostel_id: str) -> list[dict]:
        total_r = await self.session.execute(
            select(func.count(Student.id)).where(Student.hostel_id == hostel_id)
        )
        total_students = int(total_r.scalar() or 0)
        notices = await self.repository.list_by_hostel(hostel_id)
        out: list[dict] = []
        for notice in notices:
            read_r = await self.session.execute(
                select(func.count(NoticeRead.id))
                .join(Student, Student.user_id == NoticeRead.user_id)
                .where(
                    NoticeRead.notice_id == str(notice.id),
                    Student.hostel_id == hostel_id,
                )
            )
            read_count = int(read_r.scalar() or 0)
            out.append(
                {
                    "notice_id": str(notice.id),
                    "read_count": read_count,
                    "total_students": total_students,
                }
            )
        return out

    async def create_admin_notice(
        self,
        *,
        actor_id: str,
        hostel_id: str,
        payload: NoticeCreateRequest,
    ):
        notice = Notice(
            hostel_id=hostel_id if payload.scope == "hostel" else None,
            title=payload.title,
            content=payload.content,
            notice_type=payload.notice_type,
            priority=payload.priority,
            is_published=payload.is_published,
            created_by=actor_id,
        )
        notice = await self.repository.create(notice)
        await self.session.commit()
        await self.session.refresh(notice)
        return notice

    async def list_supervisor_notices(self, *, supervisor_id: str):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if not hostel_ids:
            return []
        merged: dict[str, Notice] = {}
        for hostel_id in hostel_ids:
            notices = await self.repository.list_by_hostel(hostel_id)
            for notice in notices:
                merged[str(notice.id)] = notice
        return sorted(merged.values(), key=lambda notice: notice.created_at, reverse=True)

    async def create_supervisor_notice(
        self,
        *,
        actor_id: str,
        payload: NoticeCreateRequest,
    ):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(actor_id)
        if not hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel assigned.")
        notice = Notice(
            hostel_id=hostel_ids[0],
            title=payload.title,
            content=payload.content,
            notice_type=payload.notice_type,
            priority=payload.priority,
            is_published=payload.is_published,
            created_by=actor_id,
        )
        notice = await self.repository.create(notice)
        await self.session.commit()
        await self.session.refresh(notice)
        return notice
