import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def coerce_uuids(cls, v: object) -> object:
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class TimestampedResponse(APIModel):
    id: str
    created_at: datetime
    updated_at: datetime
