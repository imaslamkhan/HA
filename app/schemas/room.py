from pydantic import BaseModel, Field

from app.schemas.base import TimestampedResponse


class RoomCreateRequest(BaseModel):
    room_number: str = Field(min_length=1, max_length=50)
    floor: int = Field(ge=0)
    room_type: str = Field(min_length=2, max_length=50)
    total_beds: int = Field(ge=1)
    daily_rent: float = Field(ge=0)
    monthly_rent: float = Field(ge=0)
    security_deposit: float = Field(ge=0)
    dimensions: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class RoomUpdateRequest(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=50)
    floor: int | None = Field(default=None, ge=0)
    room_type: str | None = Field(default=None, min_length=2, max_length=50)
    total_beds: int | None = Field(default=None, ge=1)
    daily_rent: float | None = Field(default=None, ge=0)
    monthly_rent: float | None = Field(default=None, ge=0)
    security_deposit: float | None = Field(default=None, ge=0)
    dimensions: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class BedCreateRequest(BaseModel):
    bed_number: str = Field(min_length=1, max_length=50)
    status: str = Field(default="available", min_length=2, max_length=50)


class BedUpdateRequest(BaseModel):
    bed_number: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=2, max_length=50)


class RoomResponse(TimestampedResponse):
    hostel_id: str
    room_number: str
    floor: int
    room_type: str
    total_beds: int
    daily_rent: float
    monthly_rent: float
    security_deposit: float
    dimensions: str | None = None
    is_active: bool
    available_beds: int = 0  # populated by service layer


class BedResponse(TimestampedResponse):
    hostel_id: str
    room_id: str
    bed_number: str
    status: str
