from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.student_read_repository import StudentReadRepository


class StudentReadService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = StudentReadRepository(session)

    async def get_profile(self, *, user_id: str):
        student = await self.repository.get_student_by_user(user_id)
        if student is None:
            return None
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            return None
        return {
            "id": str(student.id),
            "user_id": str(student.user_id),
            "hostel_id": str(student.hostel_id),
            "room_id": str(student.room_id),
            "bed_id": str(student.bed_id),
            "booking_id": str(student.booking_id),
            "student_number": student.student_number,
            "check_in_date": student.check_in_date,
            "check_out_date": student.check_out_date,
            "status": student.status,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "profile_picture_url": user.profile_picture_url,
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        }

    async def list_attendance(self, *, user_id: str):
        student = await self.repository.get_student_by_user(user_id)
        if student is None:
            return []
        return await self.repository.list_attendance(str(student.id))

    async def list_bookings(self, *, user_id: str):
        return await self.repository.list_bookings_by_visitor(user_id)

    async def list_notices(self, *, user_id: str):
        student = await self.repository.get_student_by_user(user_id)
        if student is None:
            return []
        return await self.repository.list_notices(str(student.hostel_id))

    async def list_mess_menus(self, *, user_id: str):
        student = await self.repository.get_student_by_user(user_id)
        if student is None:
            return []
        from app.services.mess_menu_service import _flatten_menus
        menus = await self.repository.list_mess_menus(str(student.hostel_id))
        return _flatten_menus(menus)

