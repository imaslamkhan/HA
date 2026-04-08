from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedResponse


class HostelListItem(TimestampedResponse):
    id: str
    name: str
    slug: str
    description: str
    city: str
    state: str
    hostel_type: str
    status: str
    is_public: bool
    is_featured: bool
    rating: float = 0.0
    total_reviews: int = 0
    starting_price: float = 0.0
    starting_daily_price: float = 0.0
    starting_monthly_price: float = 0.0
    available_beds: int = 0


class HostelDetailResponse(HostelListItem):
    address_line1: str
    address_line2: Optional[str] = None
    country: str
    pincode: str
    latitude: float
    longitude: float
    phone: str
    email: str
    website: Optional[str] = None
    rules_and_regulations: Optional[str] = None
    amenities: list[str] = []
    images: list[dict] = []


class PaginatedHostelListResponse(BaseModel):
    items: list[HostelListItem]
    total: int
    page: int
    per_page: int


class PublicCityResponse(BaseModel):
    city: str
    hostel_count: int


class HostelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    address_line1: str | None = Field(default=None, min_length=2, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=120)
    pincode: str | None = Field(default=None, min_length=3, max_length=20)
    phone: str | None = Field(default=None, min_length=5, max_length=30)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    is_featured: bool | None = None
    is_public: bool | None = None
    rules_and_regulations: str | None = None


class InquiryRequest(BaseModel):
    hostel_id: str
    name: str
    email: str
    phone: str
    message: str
