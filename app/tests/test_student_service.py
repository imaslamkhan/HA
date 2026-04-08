from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.booking import BookingStatus
from app.services.student_service import StudentService


@pytest.mark.asyncio
async def test_check_in_rejects_non_approved_booking() -> None:
    session = AsyncMock()
    service = StudentService(session)
    service.booking_repository = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                id="booking-1",
                status=BookingStatus.PENDING_APPROVAL,
                bed_id="bed-1",
            )
        )
    )

    with pytest.raises(HTTPException) as exc:
        await service.check_in_from_booking(booking_id="booking-1", actor_id="admin-1")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_check_in_creates_student_and_updates_states() -> None:
    session = AsyncMock()
    service = StudentService(session)
    booking = SimpleNamespace(
        id="booking-1",
        status=BookingStatus.APPROVED,
        bed_id="bed-1",
        visitor_id="user-1",
        hostel_id="hostel-1",
        room_id="room-1",
        check_in_date=None,
    )
    student = SimpleNamespace(id="student-1")
    service.booking_repository = SimpleNamespace(
        get_by_id=AsyncMock(return_value=booking),
        add_status_history=AsyncMock(),
    )
    service.student_repository = SimpleNamespace(
        get_student_by_booking=AsyncMock(return_value=None),
        create_from_booking=AsyncMock(return_value=student),
        activate_bed_stay=AsyncMock(),
        promote_user_to_student=AsyncMock(),
        set_booking_checked_in=AsyncMock(),
    )

    result = await service.check_in_from_booking(booking_id="booking-1", actor_id="admin-1")

    assert result is student
    service.student_repository.create_from_booking.assert_awaited_once()
    service.booking_repository.add_status_history.assert_awaited_once()
