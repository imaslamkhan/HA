from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceUpdateRequest
from app.services.maintenance_service import MaintenanceService


@pytest.mark.asyncio
async def test_create_supervisor_request_requires_assignment() -> None:
    session = AsyncMock()
    service = MaintenanceService(session)
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=[]))

    with pytest.raises(HTTPException) as exc:
        await service.create_supervisor_request(
            supervisor_id="sup-1",
            payload=MaintenanceCreateRequest(
                category="electrical",
                title="Broken light",
                description="Hallway light is out",
                priority="medium",
            ),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_supervisor_request_requires_hostel_access() -> None:
    session = AsyncMock()
    service = MaintenanceService(session)
    request = SimpleNamespace(id="req-1", hostel_id="hostel-1")
    service.maintenance = SimpleNamespace(get_by_id=AsyncMock(return_value=request))
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=["hostel-2"]))

    with pytest.raises(HTTPException) as exc:
        await service.update_supervisor_request(
            supervisor_id="sup-1",
            request_id="req-1",
            payload=MaintenanceUpdateRequest(status="in_progress"),
        )

    assert exc.value.status_code == 403
