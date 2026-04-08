from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.booking import BookingStatus
from app.schemas.payment import BookingPaymentCreateRequest
from app.services.payment_write_service import PaymentWriteService


@pytest.mark.asyncio
async def test_create_booking_payment_requires_matching_booking_visitor() -> None:
    session = AsyncMock()
    service = PaymentWriteService(session)
    booking = SimpleNamespace(id="booking-1", visitor_id="visitor-2", status=BookingStatus.PENDING_APPROVAL)
    service.repository = SimpleNamespace(get_booking_by_id=AsyncMock(return_value=booking))

    with pytest.raises(HTTPException) as exc:
        await service.create_booking_payment(
            booking_id="booking-1",
            actor_id="visitor-1",
            payload=BookingPaymentCreateRequest(booking_advance=1000),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_handle_razorpay_webhook_rejects_invalid_signature() -> None:
    session = AsyncMock()
    service = PaymentWriteService(session)
    service.razorpay = SimpleNamespace(verify_signature=lambda payload, signature: False)

    with pytest.raises(HTTPException) as exc:
        await service.handle_razorpay_webhook(payload={"event": "payment.captured"}, signature="bad")

    assert exc.value.status_code == 401
