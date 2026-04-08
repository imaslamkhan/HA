from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedResponse


class SuperAdminDashboardResponse(BaseModel):
    # Spec metrics
    total_hostels: int
    pending_approval_count: int
    active_hostels: int
    total_students: int
    total_revenue_month: float
    # Backward-compatible fields used by existing frontend
    hostels: int
    admins: int
    subscriptions: int


class SuperAdminHostelCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10)
    hostel_type: str
    address_line1: str = Field(min_length=2, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    country: str = Field(default="India", min_length=2, max_length=120)
    pincode: str = Field(min_length=3, max_length=20)
    latitude: float
    longitude: float
    phone: str = Field(min_length=5, max_length=30)
    email: str = Field(min_length=5, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    is_featured: bool = False
    is_public: bool = True
    rules_and_regulations: str | None = None

    from pydantic import model_validator

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_strings(cls, values: dict) -> dict:
        for field in ("website", "address_line2", "rules_and_regulations"):
            if values.get(field) == "":
                values[field] = None
        return values


class SuperAdminHostelResponse(TimestampedResponse):
    name: str
    slug: str
    description: str
    hostel_type: str
    status: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    country: str
    pincode: str
    latitude: float
    longitude: float
    phone: str
    email: str
    website: str | None = None
    is_featured: bool
    is_public: bool
    rules_and_regulations: str | None = None


class SuperAdminAdminCreateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    phone: str = Field(min_length=5, max_length=30)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class SuperAdminAdminResponse(TimestampedResponse):
    email: str
    phone: str
    full_name: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool


class AssignHostelsRequest(BaseModel):
    hostel_ids: list[str] = Field(default_factory=list, min_length=1)


class AssignHostelRequest(BaseModel):
    hostel_id: str
    is_primary: bool = False


class SuperAdminHostelListResponse(BaseModel):
    items: list[SuperAdminHostelResponse]
    total: int
    page: int
    per_page: int


class SuperAdminHostelRejectRequest(BaseModel):
    reason: str


class SuperAdminSubscriptionResponse(TimestampedResponse):
    hostel_id: str
    tier: str
    price_monthly: float
    start_date: date
    end_date: date
    status: str
    auto_renew: bool
