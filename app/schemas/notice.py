from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import APIModel


class NoticeCreateRequest(BaseModel):
    scope: str = Field(default="hostel")
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=5)
    notice_type: str = Field(min_length=2, max_length=100)
    priority: str = Field(min_length=2, max_length=50)
    is_published: bool = True


class NoticeResponse(APIModel):
    id: str
    hostel_id: str | None = None
    title: str
    content: str
    notice_type: str
    priority: str
    is_published: bool
    publish_at: datetime | None = None
    expires_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class NoticeReadStatsItem(APIModel):
    """Per-notice read counts for students assigned to the hostel (includes platform-wide notices)."""

    notice_id: str
    read_count: int
    total_students: int
