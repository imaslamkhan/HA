from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.supervisor_service import SupervisorService


@pytest.mark.asyncio
async def test_get_dashboard_aggregates_supervisor_scope() -> None:
    session = AsyncMock()
    service = SupervisorService(session)
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=["hostel-1", "hostel-2"]))
    service.admin_repository = SimpleNamespace(
        list_students_by_hostel_ids=AsyncMock(return_value=[SimpleNamespace(id="student-1"), SimpleNamespace(id="student-2")])
    )
    service.attendance_repository = SimpleNamespace(
        list_by_hostel_ids=AsyncMock(return_value=[SimpleNamespace(id="attendance-1")])
    )
    service.complaint_repository = SimpleNamespace(
        list_by_hostel=AsyncMock(side_effect=[[SimpleNamespace(id="complaint-1")], []])
    )
    service.maintenance_repository = SimpleNamespace(
        list_by_hostel=AsyncMock(side_effect=[[SimpleNamespace(id="maintenance-1")], [SimpleNamespace(id="maintenance-2")]])
    )

    result = await service.get_dashboard("supervisor-1")

    assert result.hostels == 2
    assert result.students == 2
    assert result.attendance_records == 1
    assert result.complaints == 1
    assert result.maintenance_requests == 2
