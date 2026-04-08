from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import MessMenu, MessMenuItem
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.mess_menu_repository import MessMenuRepository
from app.schemas.mess_menu import MessMenuCreateRequest


def _flatten_menus(menus: list[MessMenu]) -> list[dict]:
    """Expand each menu's items into flat dicts. One entry per item."""
    result: list[dict] = []
    for menu in menus:
        items = menu.items if menu.items else []
        if items:
            for item in items:
                result.append({
                    "id": str(item.id),
                    "hostel_id": str(menu.hostel_id),
                    "week_start_date": menu.week_start_date,
                    "is_active": menu.is_active,
                    "created_by": str(menu.created_by),
                    "created_at": menu.created_at,
                    "updated_at": menu.updated_at,
                    "day_of_week": item.day_of_week,
                    "meal_type": item.meal_type,
                    "item_name": item.item_name,
                    "is_veg": item.is_veg,
                    "special_note": item.special_note,
                })
        else:
            result.append({
                "id": str(menu.id),
                "hostel_id": str(menu.hostel_id),
                "week_start_date": menu.week_start_date,
                "is_active": menu.is_active,
                "created_by": str(menu.created_by),
                "created_at": menu.created_at,
                "updated_at": menu.updated_at,
                "day_of_week": None,
                "meal_type": None,
                "item_name": None,
                "is_veg": None,
                "special_note": None,
            })
    return result


class MessMenuService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = MessMenuRepository(session)
        self.assignments = AssignmentRepository(session)

    async def list_admin_menus(self, *, hostel_id: str):
        menus = await self.repository.list_by_hostel_with_items(hostel_id)
        return _flatten_menus(menus)

    async def create_admin_menu(self, *, actor_id: str, hostel_id: str, payload: MessMenuCreateRequest):
        menu = MessMenu(
            hostel_id=hostel_id,
            week_start_date=payload.week_start_date,
            is_active=payload.is_active,
            created_by=actor_id,
        )
        menu = await self.repository.create_menu(menu)
        item = await self.repository.create_item(
            MessMenuItem(
                menu_id=str(menu.id),
                day_of_week=payload.day_of_week,
                meal_type=payload.meal_type,
                item_name=payload.item_name,
                is_veg=payload.is_veg,
                special_note=payload.special_note,
            )
        )
        await self.session.commit()
        await self.session.refresh(menu)
        await self.session.refresh(item)
        return {
            "id": str(item.id),
            "hostel_id": str(menu.hostel_id),
            "week_start_date": menu.week_start_date,
            "is_active": menu.is_active,
            "created_by": str(menu.created_by),
            "created_at": menu.created_at,
            "updated_at": menu.updated_at,
            "day_of_week": item.day_of_week,
            "meal_type": item.meal_type,
            "item_name": item.item_name,
            "is_veg": item.is_veg,
            "special_note": item.special_note,
        }

    async def list_supervisor_menus(self, *, supervisor_id: str):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if not hostel_ids:
            return []
        menus: list[MessMenu] = []
        for hostel_id in hostel_ids:
            menus.extend(await self.repository.list_by_hostel_with_items(hostel_id))
        menus.sort(key=lambda m: m.week_start_date, reverse=True)
        return _flatten_menus(menus)

    async def list_student_menus(self, *, hostel_id: str):
        menus = await self.repository.list_by_hostel_with_items(hostel_id)
        return _flatten_menus(menus)
