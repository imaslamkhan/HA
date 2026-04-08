from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import AttendanceRecord
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.schemas.attendance import AttendanceCreateRequest


class AttendanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assignments = AssignmentRepository(session)
        self.attendance = AttendanceRepository(session)

    async def list_supervisor_attendance(self, *, supervisor_id: str):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        return await self.attendance.list_by_hostel_ids(hostel_ids)

    async def list_admin_attendance(self, *, hostel_id: str):
        return await self.attendance.list_by_hostel_ids([hostel_id])

    async def create_supervisor_attendance(
        self,
        *,
        supervisor_id: str,
        payload: AttendanceCreateRequest,
    ):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        student = await self.attendance.get_student_by_id(payload.student_id)

        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

        if str(student.hostel_id) not in hostel_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot mark attendance for this student.",
            )

        # Upsert: update existing record if one already exists for this student+date
        existing = await self.attendance.get_by_student_and_date(
            student_id=str(student.id), date=payload.date
        )
        if existing:
            existing.status = payload.status
            existing.method = payload.method
            existing.marked_by = supervisor_id
            existing.check_in_time = payload.check_in_time
            existing.check_out_time = payload.check_out_time
            existing.remarks = payload.remarks
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        record = AttendanceRecord(
            student_id=str(student.id),
            hostel_id=str(student.hostel_id),
            date=payload.date,
            check_in_time=payload.check_in_time,
            check_out_time=payload.check_out_time,
            status=payload.status,
            marked_by=supervisor_id,
            method=payload.method,
            remarks=payload.remarks,
        )
        record = await self.attendance.create(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def monthly_attendance_summary(self, *, hostel_id: str, year: int, month: int) -> list[dict]:
        rows = await self.attendance.monthly_summary_for_hostel(hostel_id, year, month)
        out: list[dict] = []
        for student_id, student_number, full_name, present_count, total_marked in rows:
            rate = (100.0 * present_count / total_marked) if total_marked else 0.0
            out.append(
                {
                    "student_id": student_id,
                    "student_number": student_number,
                    "full_name": full_name,
                    "present_count": present_count,
                    "total_marked": total_marked,
                    "attendance_rate_percent": round(rate, 1),
                }
            )
        return out
