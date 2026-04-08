from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.schemas.base import APIModel


class AttendanceCreateRequest(BaseModel):
    student_id: str
    date: date
    check_in_time: time | None = None
    check_out_time: time | None = None
    status: str = Field(min_length=2, max_length=50)
    method: str = Field(min_length=2, max_length=50)
    remarks: str | None = Field(default=None, max_length=255)


class AttendanceResponse(APIModel):
    id: str
    student_id: str
    hostel_id: str
    date: date
    check_in_time: time | None = None
    check_out_time: time | None = None
    status: str
    marked_by: str
    method: str
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime


class AttendanceMonthlySummaryItem(APIModel):
    student_id: str
    student_number: str
    full_name: str
    present_count: int
    total_marked: int
    attendance_rate_percent: float
