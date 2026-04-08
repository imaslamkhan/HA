from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, require_roles
from app.dependencies import DBSession
from app.schemas.attendance import AttendanceCreateRequest, AttendanceResponse
from app.schemas.complaint import ComplaintResponse, ComplaintUpdateRequest
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceResponse, MaintenanceUpdateRequest
from app.schemas.mess_menu import MessMenuResponse
from app.schemas.notice import NoticeCreateRequest, NoticeResponse
from app.schemas.student import StudentResponse
from app.services.admin_service import AdminService
from app.services.attendance_service import AttendanceService
from app.services.complaint_service import ComplaintService
from app.services.maintenance_service import MaintenanceService
from app.services.mess_menu_service import MessMenuService
from app.services.notice_service import NoticeService
from app.services.supervisor_service import SupervisorDashboardResponse, SupervisorService

router = APIRouter()
SupervisorUser = Annotated[CurrentUser, Depends(require_roles("supervisor"))]


@router.get("/dashboard", response_model=SupervisorDashboardResponse)
async def dashboard(current_user: SupervisorUser, db: DBSession):
    """**Supervisor dashboard** — students, complaints, attendance, maintenance counts for assigned hostel."""
    return await SupervisorService(db).get_dashboard(current_user.id)


@router.get("/students", response_model=list[StudentResponse])
async def students(current_user: SupervisorUser, db: DBSession):
    """**List students in the supervisor's assigned hostel.**"""
    hostel_ids = list(current_user.hostel_ids)
    if not hostel_ids:
        return []
    return await AdminService(db).list_students_for_hostels(hostel_ids)


@router.get("/complaints", response_model=list[ComplaintResponse])
async def complaints(current_user: SupervisorUser, db: DBSession):
    """**List complaints assigned to or visible by this supervisor.**"""
    return await ComplaintService(db).list_supervisor_complaints(supervisor_id=current_user.id)


@router.patch("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(complaint_id: str, payload: ComplaintUpdateRequest, current_user: SupervisorUser, db: DBSession):
    """**Update complaint** — change status, add resolution notes."""
    return await ComplaintService(db).update_supervisor_complaint(
        supervisor_id=current_user.id, complaint_id=complaint_id, payload=payload,
    )


@router.get("/attendance", response_model=list[AttendanceResponse])
async def attendance(current_user: SupervisorUser, db: DBSession):
    """**List attendance records** for the supervisor's hostel."""
    return await AttendanceService(db).list_supervisor_attendance(supervisor_id=current_user.id)


@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
async def mark_attendance(payload: AttendanceCreateRequest, current_user: SupervisorUser, db: DBSession):
    """
    **Mark attendance for a student.**

    - One record per student per day (enforced by DB unique constraint)
    - `status`: `present`, `absent`, `late`, `on_leave`
    - `method`: `manual`, `biometric` (biometric is phase 2)
    """
    return await AttendanceService(db).create_supervisor_attendance(
        supervisor_id=current_user.id, payload=payload,
    )


@router.get("/maintenance", response_model=list[MaintenanceResponse])
async def maintenance(current_user: SupervisorUser, db: DBSession):
    """**List maintenance requests** created by or visible to this supervisor."""
    return await MaintenanceService(db).list_supervisor_requests(supervisor_id=current_user.id)


@router.post("/maintenance", response_model=MaintenanceResponse, status_code=201)
async def create_maintenance(payload: MaintenanceCreateRequest, current_user: SupervisorUser, db: DBSession):
    """
    **Create a maintenance request.**

    If `requires_admin_approval` is true, the request will appear in the
    admin's maintenance queue for sign-off before work begins.
    """
    return await MaintenanceService(db).create_supervisor_request(
        supervisor_id=current_user.id, payload=payload,
    )


@router.patch("/maintenance/{request_id}", response_model=MaintenanceResponse)
async def update_maintenance(request_id: str, payload: MaintenanceUpdateRequest, current_user: SupervisorUser, db: DBSession):
    """**Update maintenance request** — status, vendor info, actual cost."""
    return await MaintenanceService(db).update_supervisor_request(
        supervisor_id=current_user.id, request_id=request_id, payload=payload,
    )


@router.get("/notices", response_model=list[NoticeResponse])
async def notices(current_user: SupervisorUser, db: DBSession):
    """**List notices** for the supervisor's hostel."""
    return await NoticeService(db).list_supervisor_notices(supervisor_id=current_user.id)


@router.post("/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(payload: NoticeCreateRequest, current_user: SupervisorUser, db: DBSession):
    """**Create a notice** for the hostel. Visible to all students in the hostel."""
    return await NoticeService(db).create_supervisor_notice(actor_id=current_user.id, payload=payload)


@router.get("/mess-menu", response_model=list[MessMenuResponse])
async def mess_menu(current_user: SupervisorUser, db: DBSession):
    """**View weekly mess menus** for the supervisor's hostel."""
    return await MessMenuService(db).list_supervisor_menus(supervisor_id=current_user.id)
