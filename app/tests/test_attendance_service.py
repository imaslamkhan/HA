from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.attendance import AttendanceCreateRequest
from app.services.attendance_service import AttendanceService


@pytest.mark.asyncio
async def test_list_supervisor_attendance_returns_items_for_assigned_hostels() -> None:
    session = AsyncMock()
    service = AttendanceService(session)
    expected = [SimpleNamespace(id="attendance-1")]
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=["hostel-1"]))
    service.attendance = SimpleNamespace(list_by_hostel_ids=AsyncMock(return_value=expected))

    result = await service.list_supervisor_attendance(supervisor_id="supervisor-1")

    assert result == expected
    service.attendance.list_by_hostel_ids.assert_awaited_once_with(["hostel-1"])


@pytest.mark.asyncio
async def test_list_admin_attendance_returns_items_for_hostel() -> None:
    session = AsyncMock()
    service = AttendanceService(session)
    expected = [SimpleNamespace(id="attendance-1")]
    service.attendance = SimpleNamespace(list_by_hostel_ids=AsyncMock(return_value=expected))

    result = await service.list_admin_attendance(hostel_id="hostel-1")

    assert result == expected
    service.attendance.list_by_hostel_ids.assert_awaited_once_with(["hostel-1"])


@pytest.mark.asyncio
async def test_create_supervisor_attendance_rejects_unassigned_student() -> None:
    session = AsyncMock()
    service = AttendanceService(session)
    student = SimpleNamespace(id="student-1", hostel_id="hostel-2")
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=["hostel-1"]))
    service.attendance = SimpleNamespace(
        get_student_by_id=AsyncMock(return_value=student),
        create=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_supervisor_attendance(
            supervisor_id="supervisor-1",
            payload=AttendanceCreateRequest(
                student_id="student-1",
                date="2026-03-26",
                status="present",
                method="manual",
            ),
        )

    assert exc.value.status_code == 403
