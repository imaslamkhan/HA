from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.dependencies import DBSession, CurrentUser, require_roles
from app.models.booking import Booking
from app.models.operations import MaintenanceRequest, Complaint
from app.schemas.admin import (
    AdminDashboardResponse,
    SupervisorResponse,
    SupervisorCreateRequest,
    DirectStudentAddRequest,
    DirectStudentAddResponse,
)
from app.schemas.complaint import ComplaintUpdateRequest
from app.schemas.hostel import HostelDetailResponse, HostelUpdateRequest, HostelListItem
from app.schemas.room import (
    RoomResponse,
    RoomCreateRequest,
    RoomUpdateRequest,
    BedResponse,
    BedCreateRequest,
    BedUpdateRequest,
)

from app.schemas.booking import (
    BookingResponse,
    BookingApprovalRequest,
    BookingRejectionRequest,
    BookingCancellationRequest,
)
from app.schemas.payment import PaymentResponse
from app.schemas.complaint import ComplaintResponse
from app.schemas.attendance import AttendanceResponse, AttendanceMonthlySummaryItem
from app.schemas.maintenance import MaintenanceResponse
from app.schemas.notice import NoticeResponse, NoticeReadStatsItem, NoticeCreateRequest
from app.schemas.mess_menu import MessMenuResponse, MessMenuCreateRequest
from app.schemas.student import StudentResponse
from app.services.admin_service import AdminService
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.complaint_service import ComplaintService
from app.services.attendance_service import AttendanceService
from app.services.maintenance_service import MaintenanceService
from app.services.notice_service import NoticeService
from app.services.mess_menu_service import MessMenuService

router = APIRouter()
AdminUser = Annotated[CurrentUser, Depends(require_roles("hostel_admin"))]


def _check_hostel(current_user: AdminUser, hostel_id: str) -> None:
    if hostel_id not in current_user.hostel_ids:
        raise HTTPException(status_code=403, detail="Access denied to this hostel.")


async def _resolve_room_hostel_id(db: DBSession, room_id: str) -> str:
    from app.models.room import Room
    result = await db.execute(select(Room.hostel_id).where(Room.id == room_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    return str(hostel_id)


async def _resolve_bed_hostel_id(db: DBSession, bed_id: str) -> str:
    from app.models.room import Bed
    result = await db.execute(select(Bed.hostel_id).where(Bed.id == bed_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    return str(hostel_id)


async def _resolve_booking_hostel_id(db: DBSession, booking_id: str) -> str:
    result = await db.execute(select(Booking.hostel_id).where(Booking.id == booking_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return str(hostel_id)


async def _resolve_maintenance_hostel_id(db: DBSession, request_id: str) -> str:
    result = await db.execute(select(MaintenanceRequest.hostel_id).where(MaintenanceRequest.id == request_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Maintenance request not found.")
    return str(hostel_id)


async def _resolve_complaint_hostel_id(db: DBSession, complaint_id: str) -> str:
    result = await db.execute(select(Complaint.hostel_id).where(Complaint.id == complaint_id))
    hostel_id = result.scalar_one_or_none()
    if hostel_id is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return str(hostel_id)


@router.get("/my-hostels", response_model=list[HostelListItem])
async def my_hostels(current_user: AdminUser, db: DBSession):
    """List hostels assigned to the authenticated admin."""
    return await AdminService(db).list_hostels(list(current_user.hostel_ids))


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard(current_user: AdminUser, db: DBSession, hostel_id: str | None = None):
    """Admin dashboard metrics."""
    if hostel_id:
        _check_hostel(current_user, hostel_id)
        ids = [hostel_id]
    else:
        ids = list(current_user.hostel_ids)
    return await AdminService(db).get_dashboard(ids)


@router.get("/dashboard/unified")
async def unified_dashboard(_: AdminUser):
    """Unified multi-hostel dashboard (stub)."""
    return {"hostels": 0, "revenue": 0}


@router.get("/hostels/{hostel_id}", response_model=HostelDetailResponse)
async def get_hostel(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).get_hostel(hostel_id)


@router.patch("/hostels/{hostel_id}", response_model=HostelDetailResponse)
async def update_hostel(hostel_id: str, payload: HostelUpdateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).update_hostel(hostel_id, payload)


@router.get("/hostels/{hostel_id}/bookings", response_model=list[BookingResponse])
async def list_bookings(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await BookingService(db).list_admin_bookings(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_rooms(hostel_id)


@router.post("/hostels/{hostel_id}/rooms", response_model=RoomResponse, status_code=201)
async def create_room(
    hostel_id: str,
    payload: RoomCreateRequest,
    db: DBSession,
    current_user: AdminUser
):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).create_room(hostel_id, payload)


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(room_id: str, payload: RoomUpdateRequest, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    return await AdminService(db).update_room(room_id, payload)

@router.delete("/rooms/{room_id}", status_code=204)
async def delete_room(room_id: str, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    await AdminService(db).delete_room(room_id)


@router.get("/rooms/{room_id}/beds", response_model=List[BedResponse])
async def list_beds(room_id: str, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    return await AdminService(db).list_beds(room_id)


@router.post("/rooms/{room_id}/beds", response_model=BedResponse, status_code=201)
async def create_bed(room_id: str, payload: BedCreateRequest, db: DBSession, current_user: AdminUser):
    room_hostel_id = await _resolve_room_hostel_id(db, room_id)
    _check_hostel(current_user, room_hostel_id)
    return await AdminService(db).create_bed(room_id, payload)


@router.patch("/beds/{bed_id}", response_model=BedResponse)
async def update_bed(bed_id: str, payload: BedUpdateRequest, db: DBSession, current_user: AdminUser):
    bed_hostel_id = await _resolve_bed_hostel_id(db, bed_id)
    _check_hostel(current_user, bed_hostel_id)
    return await AdminService(db).update_bed(bed_id, payload)


@router.get("/hostels/{hostel_id}/students", response_model=list[StudentResponse])
async def list_students(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_students(hostel_id)


@router.patch("/bookings/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: str,
    payload: BookingApprovalRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).approve_booking(
        booking_id=booking_id,
        approved_by=current_user.id,
        bed_id=payload.bed_id,
    )


@router.patch("/bookings/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking_endpoint(
    booking_id: str,
    payload: BookingRejectionRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).reject_booking(
        booking_id=booking_id,
        rejected_by=current_user.id,
        reason=payload.reason,
    )


@router.patch("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    payload: BookingCancellationRequest,
    db: DBSession,
    current_user: AdminUser
):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).cancel_booking(
        booking_id=booking_id,
        cancelled_by=current_user.id,
        reason=payload.reason,
    )


@router.post("/students/{booking_id}/check-in", response_model=BookingResponse)
async def check_in_student(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    from app.services.student_service import StudentService
    booking = await BookingService(db).check_in_student(booking_id=booking_id, checked_in_by=current_user.id)
    try:
        await db.refresh(booking)
        existing = await StudentService(db).student_repository.get_student_by_booking(str(booking_id))
        if existing is None:
            await StudentService(db).check_in_from_booking(booking_id=booking_id, actor_id=current_user.id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Student record creation failed for booking {booking_id}: {e}")
    return booking


@router.post("/students/{booking_id}/sync-student-record", status_code=200)
async def sync_student_record(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    from app.services.student_service import StudentService
    from app.models.booking import BookingStatus
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != BookingStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail=f"Booking is not checked_in (status: {booking.status})")
    svc = StudentService(db)
    existing = await svc.student_repository.get_student_by_booking(str(booking_id))
    if existing:
        return {"status": "already_exists", "student_id": str(existing.id)}
    student = await svc.check_in_from_booking(booking_id=booking_id, actor_id=current_user.id)
    return {"status": "created", "student_id": str(student.id)}


@router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(student_id: str, db: DBSession, current_user: AdminUser):
    from app.models.student import Student
    from pydantic import BaseModel
    class StudentUpdateRequest(BaseModel):
        status: str | None = None
        check_out_date: str | None = None
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


@router.post("/students/{booking_id}/check-out", response_model=BookingResponse)
async def check_out_student(booking_id: str, db: DBSession, current_user: AdminUser):
    booking_hostel_id = await _resolve_booking_hostel_id(db, booking_id)
    _check_hostel(current_user, booking_hostel_id)
    return await BookingService(db).check_out_student(booking_id=booking_id, checked_out_by=current_user.id)


@router.get("/hostels/{hostel_id}/payments", response_model=list[PaymentResponse])
async def list_payments(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await PaymentService(db).list_admin_payments(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/complaints", response_model=list[ComplaintResponse])
async def list_complaints(
    hostel_id: str,
    db: DBSession,
    current_user: AdminUser,
    priority: str | None = None,
    sla_filter: str | None = Query(None, description="breached | ok"),
):
    _check_hostel(current_user, hostel_id)
    return await ComplaintService(db).list_admin_complaints(
        hostel_id=hostel_id,
        priority=priority,
        sla_filter=sla_filter,
    )


@router.get("/hostels/{hostel_id}/attendance/summary", response_model=list[AttendanceMonthlySummaryItem])
async def attendance_monthly_summary(
    hostel_id: str,
    db: DBSession,
    current_user: AdminUser,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    _check_hostel(current_user, hostel_id)
    return await AttendanceService(db).monthly_attendance_summary(hostel_id=hostel_id, year=year, month=month)


@router.get("/hostels/{hostel_id}/attendance", response_model=list[AttendanceResponse])
async def list_attendance(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AttendanceService(db).list_admin_attendance(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/maintenance", response_model=list[MaintenanceResponse])
async def list_maintenance(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await MaintenanceService(db).list_admin_requests(hostel_id=hostel_id)


@router.patch("/maintenance/{request_id}/approve", response_model=MaintenanceResponse)
async def approve_maintenance(request_id: str, db: DBSession, current_user: AdminUser):
    maintenance_hostel_id = await _resolve_maintenance_hostel_id(db, request_id)
    _check_hostel(current_user, maintenance_hostel_id)
    return await MaintenanceService(db).approve_admin_request(actor_id=current_user.id, request_id=request_id)


@router.get("/hostels/{hostel_id}/notices", response_model=list[NoticeResponse])
async def list_notices(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).list_admin_notices(hostel_id=hostel_id)


@router.get("/hostels/{hostel_id}/notices/read-stats", response_model=list[NoticeReadStatsItem])
async def list_notice_read_stats(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).list_notice_read_stats(hostel_id=hostel_id)


@router.post("/hostels/{hostel_id}/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(hostel_id: str, payload: NoticeCreateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await NoticeService(db).create_admin_notice(actor_id=current_user.id, hostel_id=hostel_id, payload=payload)


@router.get("/hostels/{hostel_id}/mess-menu", response_model=list[MessMenuResponse])
async def list_mess_menu(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await MessMenuService(db).list_admin_menus(hostel_id=hostel_id)


@router.post("/hostels/{hostel_id}/mess-menu", response_model=MessMenuResponse, status_code=201)
async def create_mess_menu(hostel_id: str, payload: MessMenuCreateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await MessMenuService(db).create_admin_menu(actor_id=current_user.id, hostel_id=hostel_id, payload=payload)


@router.get("/hostels/{hostel_id}/supervisors", response_model=list[SupervisorResponse])
async def list_supervisors(hostel_id: str, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).list_supervisors(hostel_id)


@router.post("/hostels/{hostel_id}/supervisors", response_model=SupervisorResponse, status_code=201)
async def create_supervisor(hostel_id: str, payload: SupervisorCreateRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).create_supervisor(hostel_id, current_user.id, payload)


@router.post("/hostels/{hostel_id}/students/direct", response_model=DirectStudentAddResponse, status_code=201)
async def add_student_direct(hostel_id: str, payload: DirectStudentAddRequest, db: DBSession, current_user: AdminUser):
    _check_hostel(current_user, hostel_id)
    return await AdminService(db).add_student_direct(hostel_id, current_user.id, payload)


@router.patch("/hostels/{hostel_id}/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    hostel_id: str,
    complaint_id: str,
    payload: ComplaintUpdateRequest,
    db: DBSession,
    current_user: AdminUser
):
    complaint_hostel_id = await _resolve_complaint_hostel_id(db, complaint_id)
    _check_hostel(current_user, complaint_hostel_id)
    if complaint_hostel_id != hostel_id:
        raise HTTPException(status_code=400, detail="Complaint does not belong to the specified hostel.")
    return await ComplaintService(db).update_admin_complaint(hostel_id=hostel_id, complaint_id=complaint_id, payload=payload)