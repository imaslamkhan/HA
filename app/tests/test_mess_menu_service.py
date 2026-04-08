from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.mess_menu import MessMenuCreateRequest
from app.services.mess_menu_service import MessMenuService


@pytest.mark.asyncio
async def test_list_supervisor_menus_returns_empty_without_assignment() -> None:
    session = AsyncMock()
    service = MessMenuService(session)
    service.assignments = SimpleNamespace(get_supervisor_hostel_ids=AsyncMock(return_value=[]))

    result = await service.list_supervisor_menus(supervisor_id="sup-1")

    assert result == []


@pytest.mark.asyncio
async def test_create_admin_menu_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = MessMenuService(session)
    created_menu = SimpleNamespace(id="menu-1")
    service.repository = SimpleNamespace(
        create_menu=AsyncMock(return_value=created_menu),
        create_item=AsyncMock(return_value=SimpleNamespace(id="item-1")),
    )

    result = await service.create_admin_menu(
        actor_id="admin-1",
        hostel_id="hostel-1",
        payload=MessMenuCreateRequest(
            week_start_date="2026-03-30",
            meal_type="breakfast",
            item_name="Poha",
            day_of_week="monday",
        ),
    )

    assert result == created_menu
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_menu)
