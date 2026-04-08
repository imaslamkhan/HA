from datetime import date

from app.schemas.base import TimestampedResponse


class StudentProfileResponse(TimestampedResponse):
    user_id: str
    hostel_id: str
    room_id: str
    bed_id: str
    booking_id: str
    student_number: str
    check_in_date: date
    check_out_date: date | None = None
    status: str
    full_name: str
    email: str
    phone: str
    profile_picture_url: str | None = None


class StudentResponse(TimestampedResponse):
    user_id: str
    hostel_id: str
    room_id: str
    bed_id: str
    booking_id: str
    student_number: str
    check_in_date: str
    check_out_date: str | None
    status: str
    full_name: str
    email: str
    phone: str
    profile_picture_url: str | None
