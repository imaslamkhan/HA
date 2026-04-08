from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.notice import NoticeCreateRequest
from app.services.notice_service import NoticeService


@pytest.mark.asyncio
async def test_list_admin_notices_delegates_to_repository() -> None:
    session = AsyncMock()
    service = NoticeService(session)
    expected = [SimpleNamespace(id="notice-1")]
    service.repository = SimpleNamespace(list_by_hostel=AsyncMock(return_value=expected))

    result = await service.list_admin_notices(hostel_id="hostel-1")

    assert result == expected
    service.repository.list_by_hostel.assert_awaited_once_with("hostel-1")


@pytest.mark.asyncio
async def test_create_admin_notice_sets_platform_scope_hostel_id_to_none() -> None:
    session = AsyncMock()
    service = NoticeService(session)
    created_notice = SimpleNamespace(id="notice-1")
    service.repository = SimpleNamespace(create=AsyncMock(return_value=created_notice))

    result = await service.create_admin_notice(
        actor_id="admin-1",
        hostel_id="hostel-1",
        payload=NoticeCreateRequest(
            scope="platform",
            title="Platform advisory",
            content="Water supply timing has changed.",
            notice_type="operations",
            priority="high",
            is_published=True,
        ),
    )

    assert result == created_notice
    created_model = service.repository.create.await_args.args[0]
    assert created_model.hostel_id is None
    assert created_model.created_by == "admin-1"
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_notice)


@pytest.mark.asyncio
async def test_list_supervisor_notices_returns_empty_without_assignment() -> None:
    session = AsyncMock()
    service = NoticeService(session)
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=[]))

    result = await service.list_supervisor_notices(supervisor_id="sup-1")

    assert result == []
