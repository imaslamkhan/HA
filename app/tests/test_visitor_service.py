from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.visitor_service import VisitorService


@pytest.mark.asyncio
async def test_list_bookings_delegates_to_repository() -> None:
    session = AsyncMock()
    service = VisitorService(session)
    expected = [SimpleNamespace(id="booking-1")]
    service.repository = SimpleNamespace(list_bookings=AsyncMock(return_value=expected))

    result = await service.list_bookings("visitor-1")

    assert result == expected
