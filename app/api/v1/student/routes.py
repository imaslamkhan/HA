from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response
from sqlalchemy import or_, select

from app.dependencies import CurrentUser, DBSession, require_roles
from app.models.operations import Notice, NoticeRead
from app.schemas.attendance import AttendanceResponse
from app.schemas.booking import BookingResponse, WaitlistEntryResponse
from app.schemas.complaint import ComplaintCreateRequest, ComplaintResponse
from app.schemas.mess_menu import MessMenuResponse
from app.schemas.notice import NoticeResponse
from app.schemas.payment import PaymentResponse
from app.schemas.student import StudentProfileResponse
from app.schemas.upload import PresignedUploadRequest, PresignedUploadResponse
from app.integrations.s3 import get_s3_client
from app.services.booking_service import BookingService
from app.services.complaint_service import ComplaintService
from app.services.payment_service import PaymentService
from app.services.student_read_service import StudentReadService

router = APIRouter()
StudentUser = Annotated[CurrentUser, Depends(require_roles("student"))]


@router.get("/profile", response_model=StudentProfileResponse)
async def profile(current_user: StudentUser, db: DBSession):
    """**Student profile** — personal info, hostel, room, bed, booking, and student number."""
    profile_data = await StudentReadService(db).get_profile(user_id=current_user.id)
    if profile_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )
    return profile_data


@router.get("/payments", response_model=list[PaymentResponse])
async def payments(current_user: StudentUser, db: DBSession):
    """**Student payment history** — booking advances, monthly rent, and payment statuses."""
    return await PaymentService(db).list_student_payments(user_id=current_user.id)


@router.get("/bookings", response_model=list[BookingResponse])
async def bookings(current_user: StudentUser, db: DBSession):
    """**Student booking history** — all bookings in all statuses."""
    return await StudentReadService(db).list_bookings(user_id=current_user.id)


@router.get("/attendance", response_model=list[AttendanceResponse])
async def attendance(current_user: StudentUser, db: DBSession):
    """**Student attendance records** — daily check-in/check-out history."""
    return await StudentReadService(db).list_attendance(user_id=current_user.id)


@router.get("/notices", response_model=list[NoticeResponse])
async def notices(current_user: StudentUser, db: DBSession):
    """**Notices for the student's hostel** — published notices only."""
    return await StudentReadService(db).list_notices(user_id=current_user.id)


@router.api_route("/notices/{notice_id}/read", methods=["POST", "PATCH"])
async def mark_notice_read(notice_id: str, current_user: StudentUser, db: DBSession):
    student = await StudentReadService(db).repository.get_student_by_user(current_user.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    notice_result = await db.execute(
        select(Notice).where(
            Notice.id == notice_id,
            Notice.is_published.is_(True),
            or_(Notice.hostel_id == str(student.hostel_id), Notice.hostel_id.is_(None)),
        )
    )
    notice = notice_result.scalar_one_or_none()
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found.")
    existing_result = await db.execute(
        select(NoticeRead).where(
            NoticeRead.notice_id == notice_id,
            NoticeRead.user_id == current_user.id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is None:
        db.add(NoticeRead(notice_id=notice_id, user_id=current_user.id))
        await db.commit()
    return {"notice_id": notice_id, "is_read": True}


@router.get("/notices/read-status", response_model=list[str])
async def notice_read_status(current_user: StudentUser, db: DBSession):
    student = await StudentReadService(db).repository.get_student_by_user(current_user.id)
    if student is None:
        return []
    result = await db.execute(
        select(NoticeRead.notice_id)
        .join(Notice, Notice.id == NoticeRead.notice_id)
        .where(
            NoticeRead.user_id == current_user.id,
            Notice.is_published.is_(True),
            or_(Notice.hostel_id == str(student.hostel_id), Notice.hostel_id.is_(None)),
        )
    )
    return [str(notice_id) for notice_id in result.scalars().all()]


@router.get("/mess-menu", response_model=list[MessMenuResponse])
async def mess_menu(current_user: StudentUser, db: DBSession):
    """**Weekly mess menu** for the student's hostel."""
    return await StudentReadService(db).list_mess_menus(user_id=current_user.id)


@router.get("/waitlist", response_model=list[WaitlistEntryResponse])
async def student_waitlist(current_user: StudentUser, db: DBSession):
    """**Visitor waitlist entries** for the same account (user id matches waitlist visitor_id)."""
    return await BookingService(db).list_my_waitlist(visitor_id=current_user.id)


@router.delete("/waitlist/{entry_id}", status_code=204)
async def student_leave_waitlist(entry_id: str, current_user: StudentUser, db: DBSession):
    await BookingService(db).leave_waitlist(visitor_id=current_user.id, entry_id=entry_id)
    return Response(status_code=204)


@router.get("/complaints", response_model=list[ComplaintResponse])
async def complaints(current_user: StudentUser, db: DBSession):
    """**Student's own complaints** — submitted complaints with current status."""
    return await ComplaintService(db).list_student_complaints(user_id=current_user.id)


@router.post("/complaints", response_model=ComplaintResponse, status_code=201)
async def create_complaint(payload: ComplaintCreateRequest, current_user: StudentUser, db: DBSession):
    """
    **Submit a new complaint.**

    - `category`: `maintenance`, `food`, `security`, `cleanliness`, `other`
    - `priority`: `low`, `medium`, `high`, `urgent`
    - Complaint is assigned a unique `complaint_number` for tracking
    """
    return await ComplaintService(db).create_student_complaint(user_id=current_user.id, payload=payload)


@router.post("/uploads/presigned-url", response_model=PresignedUploadResponse)
async def create_presigned_upload_url(
    payload: PresignedUploadRequest,
    current_user: Annotated[CurrentUser, Depends(require_roles("student", "visitor", "hostel_admin", "super_admin"))],
):
    """Generate S3 presigned upload URL for student complaint attachments."""
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
    content_type = payload.content_type.strip().lower()
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: jpg, png, webp, pdf.",
        )
    if payload.file_size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit.",
        )
    return await get_s3_client().get_presigned_upload_url(
        file_name=payload.file_name,
        content_type=content_type,
    )


# ── Additional student endpoints ──────────────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel

class StudentProfileUpdateRequest(PydanticBaseModel):
    full_name: str | None = None
    phone: str | None = None
    profile_picture_url: str | None = None


class LeaveRequestCreate(PydanticBaseModel):
    from_date: str
    to_date: str
    reason: str


@router.patch("/profile")
async def update_profile(payload: StudentProfileUpdateRequest, current_user: StudentUser, db: DBSession):
    """**Update student profile** — name, phone, profile picture."""
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.full_name:
        user.full_name = payload.full_name
    if payload.phone:
        user.phone = payload.phone
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    await db.commit()
    await db.refresh(user)
    return {"id": str(user.id), "full_name": user.full_name, "email": user.email,
            "phone": user.phone, "profile_picture_url": user.profile_picture_url}


@router.get("/room-info")
async def room_info(current_user: StudentUser, db: DBSession):
    """**Get student's current room and bed details.**"""
    from sqlalchemy import select
    from app.models.student import Student
    from app.models.room import Room, Bed
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found.")
    room_result = await db.execute(select(Room).where(Room.id == student.room_id))
    room = room_result.scalar_one_or_none()
    bed_result = await db.execute(select(Bed).where(Bed.id == student.bed_id))
    bed = bed_result.scalar_one_or_none()
    return {
        "student_number": student.student_number,
        "room": {
            "id": str(room.id) if room else None,
            "room_number": room.room_number if room else None,
            "floor": room.floor if room else None,
            "room_type": room.room_type if room else None,
            "monthly_rent": float(room.monthly_rent) if room else None,
        },
        "bed": {
            "id": str(bed.id) if bed else None,
            "bed_number": bed.bed_number if bed else None,
            "status": bed.status if bed else None,
        },
        "check_in_date": str(student.check_in_date),
        "check_out_date": str(student.check_out_date) if student.check_out_date else None,
        "status": student.status,
    }


@router.post("/leave-request", status_code=201)
async def create_leave_request(payload: LeaveRequestCreate, current_user: StudentUser, db: DBSession):
    """**Apply for leave.** Creates a leave request for admin approval."""
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found.")
    # Store as a notice/complaint for now — a dedicated LeaveRequest model can be added later
    from app.models.operations import Complaint
    import uuid
    leave = Complaint(
        complaint_number=f"LVE-{uuid.uuid4().hex[:6].upper()}",
        student_id=student.id,
        hostel_id=student.hostel_id,
        category="other",
        title=f"Leave Request: {payload.from_date} to {payload.to_date}",
        description=f"Leave from {payload.from_date} to {payload.to_date}. Reason: {payload.reason}",
        priority="low",
        status="open",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return {"message": "Leave request submitted.", "reference": leave.complaint_number,
            "from_date": payload.from_date, "to_date": payload.to_date}
