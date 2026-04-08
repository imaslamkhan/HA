from datetime import date

import pytest

from app.schemas.booking import BookingCreateRequest


def test_booking_create_request_rejects_invalid_dates() -> None:
    with pytest.raises(ValueError):
        BookingCreateRequest(
            hostel_id="1",
            room_id="1",
            booking_mode="daily",
            check_in_date=date(2026, 3, 27),
            check_out_date=date(2026, 3, 27),
            full_name="Test User",
            booking_advance=1000,
        )
