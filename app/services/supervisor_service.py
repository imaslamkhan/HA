from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.maintenance_repository import MaintenanceRepository
from app.services.notice_service import NoticeService


class SupervisorDashboardResponse(BaseModel):
    students: int
    complaints: int
    attendance_records: int
    maintenance_requests: int
    notices: int
    hostels: int


class SupervisorService:
    def __init__(self, session: AsyncSession) -> None:
        self.assignments = AssignmentRepository(session)
        self.admin_repository = AdminRepository(session)
        self.attendance_repository = AttendanceRepository(session)
        self.complaint_repository = ComplaintRepository(session)
        self.maintenance_repository = MaintenanceRepository(session)
        self.notice_service = NoticeService(session)

    async def get_dashboard(self, supervisor_id: str) -> SupervisorDashboardResponse:
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        students = await self.admin_repository.list_students_by_hostel_ids(hostel_ids)
        attendance_records = await self.attendance_repository.list_by_hostel_ids(hostel_ids)

        complaints_count = 0
        maintenance_count = 0
        for hostel_id in hostel_ids:
            complaints = await self.complaint_repository.list_by_hostel(hostel_id)
            maintenance = await self.maintenance_repository.list_by_hostel(hostel_id)
            complaints_count += len(complaints)
            maintenance_count += len(maintenance)
        notices = await self.notice_service.list_supervisor_notices(supervisor_id=supervisor_id)

        return SupervisorDashboardResponse(
            students=len(students),
            complaints=complaints_count,
            attendance_records=len(attendance_records),
            maintenance_requests=maintenance_count,
            notices=len(notices),
            hostels=len(hostel_ids),
        )
