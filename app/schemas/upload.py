from pydantic import BaseModel, Field


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)
    file_size: int = Field(gt=0, le=10 * 1024 * 1024)


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_url: str
    filename: str
