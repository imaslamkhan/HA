from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.room import BedCreateRequest, RoomCreateRequest
from app.schemas.hostel import HostelUpdateRequest
from app.schemas.admin import SupervisorCreateRequest
from app.services.admin_service import AdminService


@pytest.mark.asyncio
async def test_list_rooms_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="room-1")]
    service.repository = SimpleNamespace(
        list_rooms=AsyncMock(return_value=expected),
        list_students=AsyncMock(),
    )

    result = await service.list_rooms("hostel-1")

    assert result == expected


@pytest.mark.asyncio
async def test_list_students_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="student-1")]
    service.repository = SimpleNamespace(
        list_rooms=AsyncMock(),
        list_students=AsyncMock(return_value=expected),
    )

    result = await service.list_students("hostel-1")

    assert result == expected


@pytest.mark.asyncio
async def test_list_students_for_hostels_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="student-1"), SimpleNamespace(id="student-2")]
    service.repository = SimpleNamespace(
        list_students_by_hostel_ids=AsyncMock(return_value=expected),
    )

    result = await service.list_students_for_hostels(["hostel-1", "hostel-2"])

    assert result == expected
    service.repository.list_students_by_hostel_ids.assert_awaited_once_with(["hostel-1", "hostel-2"])


@pytest.mark.asyncio
async def test_list_attendance_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="attendance-1")]
    service.repository = SimpleNamespace(
        list_attendance=AsyncMock(return_value=expected),
    )

    result = await service.list_attendance("hostel-1")

    assert result == expected
    service.repository.list_attendance.assert_awaited_once_with("hostel-1")


@pytest.mark.asyncio
async def test_create_room_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = AdminService(session)
    created_room = SimpleNamespace(id="room-1")
    service.repository = SimpleNamespace(create_room=AsyncMock(return_value=created_room))

    result = await service.create_room(
        "hostel-1",
        RoomCreateRequest(
            room_number="101",
            floor=1,
            room_type="single",
            total_beds=1,
            daily_rent=500,
            monthly_rent=9000,
            security_deposit=2000,
        ),
    )

    assert result == created_room
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_room)


@pytest.mark.asyncio
async def test_create_bed_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = AdminService(session)
    created_bed = SimpleNamespace(id="bed-1")
    service.repository = SimpleNamespace(create_bed=AsyncMock(return_value=created_bed))

    result = await service.create_bed(
        "hostel-1",
        "room-1",
        BedCreateRequest(bed_number="B1", status="available"),
    )

    assert result == created_bed
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_bed)


@pytest.mark.asyncio
async def test_update_hostel_commits_and_refreshes() -> None:
    session = AsyncMock()
    hostel = SimpleNamespace(id="hostel-1", name="Old Name", city="Pune")
    service = AdminService(session)
    service.repository = SimpleNamespace(get_hostel_by_id=AsyncMock(return_value=hostel))

    result = await service.update_hostel(
        "hostel-1",
        HostelUpdateRequest(name="New Name", city="Mumbai"),
    )

    assert result == hostel
    assert hostel.name == "New Name"
    assert hostel.city == "Mumbai"
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(hostel)


@pytest.mark.asyncio
async def test_list_supervisors_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="supervisor-1")]
    service.repository = SimpleNamespace(list_supervisors=AsyncMock(return_value=expected))

    result = await service.list_supervisors("hostel-1")

    assert result == expected
    service.repository.list_supervisors.assert_awaited_once_with("hostel-1")


@pytest.mark.asyncio
async def test_list_hostels_delegates_to_repository() -> None:
    session = AsyncMock()
    service = AdminService(session)
    expected = [SimpleNamespace(id="hostel-1")]
    service.repository = SimpleNamespace(list_hostels_by_ids=AsyncMock(return_value=expected))

    result = await service.list_hostels(["hostel-1"])

    assert result == expected
    service.repository.list_hostels_by_ids.assert_awaited_once_with(["hostel-1"])


@pytest.mark.asyncio
async def test_create_supervisor_commits_and_refreshes() -> None:
    session = AsyncMock()
    service = AdminService(session)
    created_supervisor = SimpleNamespace(id="supervisor-1")
    service.repository = SimpleNamespace(
        create_supervisor=AsyncMock(return_value=created_supervisor),
        assign_supervisor_to_hostel=AsyncMock(),
    )

    result = await service.create_supervisor(
        "hostel-1",
        "admin-1",
        SupervisorCreateRequest(
            email="supervisor@example.com",
            phone="9999999997",
            full_name="Supervisor User",
            password="Password123",
        ),
    )

    assert result == created_supervisor
    service.repository.assign_supervisor_to_hostel.assert_awaited_once_with(
        supervisor_id="supervisor-1",
        hostel_id="hostel-1",
        assigned_by="admin-1",
    )
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_supervisor)


@pytest.mark.asyncio
async def test_get_dashboard_aggregates_hostel_scope() -> None:
    session = AsyncMock()
    service = AdminService(session)
    service.repository = SimpleNamespace(
        list_hostels_by_ids=AsyncMock(return_value=[SimpleNamespace(id="hostel-1"), SimpleNamespace(id="hostel-2")]),
        list_rooms=AsyncMock(side_effect=[[SimpleNamespace(id="room-1")], [SimpleNamespace(id="room-2"), SimpleNamespace(id="room-3")]]),
        list_students=AsyncMock(side_effect=[[SimpleNamespace(id="student-1")], []]),
    )
    service.complaints = SimpleNamespace(
        list_by_hostel=AsyncMock(side_effect=[[SimpleNamespace(id="complaint-1")], [SimpleNamespace(id="complaint-2")]])
    )
    service.maintenance = SimpleNamespace(
        list_by_hostel=AsyncMock(side_effect=[[SimpleNamespace(id="maintenance-1")], []])
    )
    service.payments = SimpleNamespace(
        list_by_hostel=AsyncMock(side_effect=[[SimpleNamespace(id="payment-1")], [SimpleNamespace(id="payment-2")]])
    )

    result = await service.get_dashboard(["hostel-1", "hostel-2"])

    assert result["hostels"] == 2
    assert result["rooms"] == 3
    assert result["students"] == 1
    assert result["complaints"] == 2
    assert result["maintenance_items"] == 1
    assert result["payments"] == 2
