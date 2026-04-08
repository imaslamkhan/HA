from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import APIModel


class MaintenanceCreateRequest(BaseModel):
    room_id: str | None = None
    category: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    priority: str = Field(min_length=2, max_length=50)
    estimated_cost: float | None = None


class MaintenanceUpdateRequest(BaseModel):
    status: str | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    assigned_vendor_name: str | None = None
    vendor_contact: str | None = None
    requires_admin_approval: bool | None = None


class MaintenanceResponse(APIModel):
    id: str
    hostel_id: str
    room_id: str | None = None
    reported_by: str
    category: str
    title: str
    description: str
    priority: str
    status: str
    estimated_cost: float | None = None
    actual_cost: float | None = None
    assigned_vendor_name: str | None = None
    vendor_contact: str | None = None
    requires_admin_approval: bool
    approved_by: str | None = None
    created_at: datetime
    updated_at: datetime
