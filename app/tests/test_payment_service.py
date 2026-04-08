from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.payment_service import PaymentService


@pytest.mark.asyncio
async def test_list_student_payments_returns_empty_without_student_profile() -> None:
    session = AsyncMock()
    service = PaymentService(session)
    service.repository = SimpleNamespace(get_student_by_user=AsyncMock(return_value=None))

    result = await service.list_student_payments(user_id="user-1")

    assert result == []


@pytest.mark.asyncio
async def test_list_admin_payments_delegates_by_hostel() -> None:
    session = AsyncMock()
    service = PaymentService(session)
    expected = [SimpleNamespace(id="payment-1")]
    service.repository = SimpleNamespace(list_by_hostel=AsyncMock(return_value=expected))

    result = await service.list_admin_payments(hostel_id="hostel-1")

    assert result == expected
    service.repository.list_by_hostel.assert_awaited_once_with("hostel-1")
