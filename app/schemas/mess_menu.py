from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.base import APIModel


class MessMenuCreateRequest(BaseModel):
    week_start_date: date
    is_active: bool = True
    meal_type: str = Field(min_length=2, max_length=50)
    item_name: str = Field(min_length=2, max_length=255)
    day_of_week: str = Field(min_length=2, max_length=20)
    is_veg: bool = True
    special_note: str | None = Field(default=None, max_length=255)


class MessMenuItemResponse(APIModel):
    id: str
    menu_id: str
    day_of_week: str
    meal_type: str
    item_name: str
    is_veg: bool
    special_note: str | None = None


class MessMenuResponse(APIModel):
    id: str
    hostel_id: str
    week_start_date: date
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    # Flattened item fields — populated from the first (and typically only) item per entry
    day_of_week: str | None = None
    meal_type: str | None = None
    item_name: str | None = None
    is_veg: bool | None = None
    special_note: str | None = None

    model_config = {"from_attributes": True}
