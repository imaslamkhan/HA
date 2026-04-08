from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.complaint import ComplaintCreateRequest, ComplaintUpdateRequest
from app.services.complaint_service import ComplaintService


@pytest.mark.asyncio
async def test_create_student_complaint_requires_student_profile() -> None:
    session = AsyncMock()
    service = ComplaintService(session)
    service.assignments = SimpleNamespace(get_student_by_user=AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        await service.create_student_complaint(
            user_id="user-1",
            payload=ComplaintCreateRequest(
                category="maintenance",
                title="Broken fan",
                description="Fan is not working",
                priority="medium",
            ),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_supervisor_complaint_requires_hostel_access() -> None:
    session = AsyncMock()
    service = ComplaintService(session)
    complaint = SimpleNamespace(id="cmp-1", hostel_id="hostel-1")
    service.complaints = SimpleNamespace(get_by_id=AsyncMock(return_value=complaint))
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=["hostel-2"]))

    with pytest.raises(HTTPException) as exc:
        await service.update_supervisor_complaint(
            supervisor_id="sup-1",
            complaint_id="cmp-1",
            payload=ComplaintUpdateRequest(status="resolved"),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_admin_complaint_requires_matching_hostel() -> None:
    session = AsyncMock()
    service = ComplaintService(session)
    complaint = SimpleNamespace(id="cmp-1", hostel_id="hostel-1")
    service.complaints = SimpleNamespace(get_by_id=AsyncMock(return_value=complaint))

    with pytest.raises(HTTPException) as exc:
        await service.update_admin_complaint(
            hostel_id="hostel-2",
            complaint_id="cmp-1",
            payload=ComplaintUpdateRequest(status="resolved"),
        )

    assert exc.value.status_code == 403
