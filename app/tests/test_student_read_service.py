from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.student_read_service import StudentReadService


@pytest.mark.asyncio
async def test_list_notices_returns_empty_without_student_profile() -> None:
    session = AsyncMock()
    service = StudentReadService(session)
    service.repository = SimpleNamespace(get_student_by_user=AsyncMock(return_value=None))

    result = await service.list_notices(user_id="user-1")

    assert result == []


@pytest.mark.asyncio
async def test_list_attendance_delegates_for_existing_student() -> None:
    session = AsyncMock()
    service = StudentReadService(session)
    student = SimpleNamespace(id="student-1", hostel_id="hostel-1")
    expected = [SimpleNamespace(id="attendance-1")]
    service.repository = SimpleNamespace(
        get_student_by_user=AsyncMock(return_value=student),
        list_attendance=AsyncMock(return_value=expected),
        list_notices=AsyncMock(),
        list_mess_menus=AsyncMock(),
    )

    result = await service.list_attendance(user_id="user-1")

    assert result == expected


@pytest.mark.asyncio
async def test_get_profile_returns_none_without_student_profile() -> None:
    session = AsyncMock()
    service = StudentReadService(session)
    service.repository = SimpleNamespace(get_student_by_user=AsyncMock(return_value=None))

    result = await service.get_profile(user_id="user-1")

    assert result is None


@pytest.mark.asyncio
async def test_list_bookings_returns_student_booking_history() -> None:
    session = AsyncMock()
    service = StudentReadService(session)
    student = SimpleNamespace(id="student-1", booking_id="booking-1")
    expected = [SimpleNamespace(id="booking-1")]
    service.repository = SimpleNamespace(
        get_student_by_user=AsyncMock(return_value=student),
        list_bookings=AsyncMock(return_value=expected),
    )

    result = await service.list_bookings(user_id="user-1")

    assert result == expected
    service.repository.list_bookings.assert_awaited_once_with("booking-1")
