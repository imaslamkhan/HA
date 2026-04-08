"""
Admin service – hostel management operations.
"""
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.models.booking import Booking, BookingMode, BookingStatus, BedStay, BedStayStatus
from app.models.hostel import AdminHostelMapping, Hostel, HostelStatus
from app.models.operations import Complaint, MaintenanceRequest
from app.models.payment import Payment
from app.models.room import Bed, BedStatus, Room, RoomType
from app.models.student import Student, StudentStatus
from app.models.user import User, UserRole
from app.repositories.admin_repository import AdminRepository
from app.schemas.room import RoomCreateRequest, RoomUpdateRequest, BedCreateRequest, BedUpdateRequest
from app.schemas.hostel import HostelUpdateRequest
from app.schemas.admin import SupervisorCreateRequest
from app.services.complaint_service import ComplaintService
from app.services.maintenance_service import MaintenanceService
from app.services.payment_service import PaymentService
from app.repositories.room_repository import RoomRepository


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AdminRepository(session)
        self.complaints = ComplaintService(session)
        self.maintenance = MaintenanceService(session)
        self.payments = PaymentService(session)

    async def list_hostels(self, hostel_ids: list[str]) -> list[Hostel]:
        """List hostels by IDs."""
        return await self.repository.list_hostels_by_ids(hostel_ids)

    async def get_hostel(self, hostel_id: str) -> Hostel | None:
        """Get a single hostel by ID."""
        return await self.repository.get_hostel_by_id(hostel_id)

    async def update_hostel(self, hostel_id: str, payload: HostelUpdateRequest) -> Hostel:
        """Update hostel details."""
        hostel = await self.repository.get_hostel_by_id(hostel_id)
        if hostel is None:
            raise HTTPException(status_code=404, detail="Hostel not found.")
        update_data = payload.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(hostel, field, value)
        await self.session.commit()
        await self.session.refresh(hostel)
        return hostel

    async def list_rooms(self, hostel_id: str):
        rooms = await self.repository.list_rooms(hostel_id)

        for room in rooms:
            room.available_beds = await RoomRepository.get_available_bed_count(
                self=self,
                room_id=room.id,
                start_date=date.today(),
                end_date=date.today()
            )

        return rooms

    async def create_room(self, hostel_id: str, payload: RoomCreateRequest) -> Room:
        """
        Create a new room in a hostel and automatically create its beds.
        
        Fixed bug: bed_number now uses instance attribute room.room_number 
        instead of class attribute Room.room_number which created invalid SQL.
        """
        # Create the room
        room = Room(
            hostel_id=hostel_id,
            room_number=payload.room_number,
            floor=payload.floor,
            room_type=payload.room_type,
            total_beds=payload.total_beds,
            daily_rent=payload.daily_rent,
            monthly_rent=payload.monthly_rent,
            security_deposit=payload.security_deposit,
            dimensions=payload.dimensions,
            is_active=True,
        )
        self.session.add(room)
        await self.session.flush()  # ← Obtain room.id
        
        # ✅ FIX: Use instance attribute room.room_number (string value)
        # instead of class attribute Room.room_number (SQL column expression)
        for i in range(room.total_beds):
            bed = Bed(
                hostel_id=hostel_id,
                room_id=str(room.id),
                bed_number=f"{room.room_number}-B{i + 1}",  # ✅ CORRECT
                # Example: "101-B1", "101-B2", etc.
                status=BedStatus.AVAILABLE,
            )
            self.session.add(bed)

        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def update_room(self, room_id: str, payload: RoomUpdateRequest) -> Room:
        """Update room details."""
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        update_data = payload.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(room, field, value)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def list_beds(self, room_id: str) -> list[Bed]:
        """List all beds in a room."""
        return await self.repository.list_beds(room_id)

    async def create_bed(self, room_id: str, payload: BedCreateRequest) -> Bed:
        """Add a bed to a room."""
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        bed = Bed(
            hostel_id=room.hostel_id,
            room_id=room_id,
            bed_number=payload.bed_number,
            status=payload.status or BedStatus.AVAILABLE,
        )
        self.session.add(bed)
        room.total_beds += 1
        await self.session.commit()
        await self.session.refresh(bed)
        return bed

    async def update_bed(self, bed_id: str, payload: BedUpdateRequest) -> Bed:
        """Update bed status (e.g., set to maintenance)."""
        bed = await self.repository.get_bed_by_id(bed_id)
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found.")
        if payload.status is not None:
            bed.status = payload.status
        await self.session.commit()
        await self.session.refresh(bed)
        return bed

    async def list_students(self, hostel_id: str) -> list[Student]:
        """List all checked-in students for a hostel."""
        return await self.repository.list_students(hostel_id)

    async def list_students_for_hostels(self, hostel_ids: list[str]) -> list[Student]:
        """List students across multiple hostels."""
        return await self.repository.list_students_by_hostel_ids(hostel_ids)

    async def list_attendance(self, hostel_id: str):
        """List attendance records for a hostel."""
        return await self.repository.list_attendance(hostel_id)

    async def get_dashboard(self, hostel_ids: list[str]) -> dict:
        """Admin dashboard metrics."""
        if not hostel_ids:
            return {"hostels": 0, "rooms": 0, "students": 0,
                    "complaints": 0, "maintenance_items": 0, "payments": 0}
        rooms = await self.session.execute(
            select(func.count()).select_from(Room).where(Room.hostel_id.in_(hostel_ids))
        )
        students = await self.session.execute(
            select(func.count()).select_from(Student).where(Student.hostel_id.in_(hostel_ids))
        )
        complaints = await self.session.execute(
            select(func.count()).select_from(Complaint).where(Complaint.hostel_id.in_(hostel_ids))
        )
        maintenance = await self.session.execute(
            select(func.count()).select_from(MaintenanceRequest).where(MaintenanceRequest.hostel_id.in_(hostel_ids))
        )
        payments = await self.session.execute(
            select(func.count()).select_from(Payment).where(Payment.hostel_id.in_(hostel_ids))
        )
        return {
            "hostels": len(hostel_ids),
            "rooms": int(rooms.scalar_one() or 0),
            "students": int(students.scalar_one() or 0),
            "complaints": int(complaints.scalar_one() or 0),
            "maintenance_items": int(maintenance.scalar_one() or 0),
            "payments": int(payments.scalar_one() or 0),
        }

    async def list_supervisors(self, hostel_id: str):
        """List supervisors assigned to a hostel."""
        return await self.repository.list_supervisors(hostel_id)

    async def create_supervisor(self, hostel_id: str, assigned_by: str, payload: SupervisorCreateRequest) -> User:
        """Create a supervisor and assign to hostel."""
        user = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.SUPERVISOR,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.repository.assign_supervisor_to_hostel(
            supervisor_id=str(user.id),
            hostel_id=hostel_id,
            assigned_by=assigned_by,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def add_student_direct(self, hostel_id: str, actor_id: str, payload):
        bed_result = await self.session.execute(select(Bed).where(Bed.id == payload.bed_id))
        bed = bed_result.scalar_one_or_none()
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found.")
        if str(bed.hostel_id) != hostel_id:
            raise HTTPException(status_code=400, detail="Bed does not belong to this hostel.")

        user = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.STUDENT,
            is_active=True,
            is_email_verified=True,
            is_phone_verified=True,
        )
        try:
            self.session.add(user)
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            err_str = str(e).lower()
            if "ix_users_email" in err_str:
                raise HTTPException(status_code=409, detail="A user with this email already exists.")
            if "ix_users_phone" in err_str:
                raise HTTPException(status_code=409, detail="A user with this phone number already exists.")
            raise

        check_in = date.fromisoformat(payload.check_in_date)
        check_out = date.fromisoformat(payload.check_out_date)
        booking_number = f"SE-{str(user.id)[:8].upper()}"

        booking = Booking(
            visitor_id=str(user.id),
            hostel_id=hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            booking_number=booking_number,
            booking_mode=BookingMode(payload.booking_mode),
            check_in_date=check_in,
            check_out_date=check_out,
            base_rent_amount=0,
            security_deposit=0,
            booking_advance=0,
            grand_total=0,
            status=BookingStatus.CHECKED_IN,
            full_name=payload.full_name,
            approved_by=actor_id,
        )
        self.session.add(booking)
        await self.session.flush()

        bed_stay = BedStay(
            hostel_id=hostel_id,
            bed_id=payload.bed_id,
            booking_id=str(booking.id),
            start_date=check_in,
            end_date=check_out,
            status=BedStayStatus.ACTIVE,
        )
        self.session.add(bed_stay)

        bed.status = BedStatus.OCCUPIED

        student_number = f"STU-{str(booking.id)[:8].upper()}"
        student = Student(
            user_id=str(user.id),
            hostel_id=hostel_id,
            room_id=payload.room_id,
            bed_id=payload.bed_id,
            booking_id=str(booking.id),
            student_number=student_number,
            check_in_date=check_in,
            check_out_date=check_out,
            status=StudentStatus.ACTIVE,
        )
        self.session.add(student)

        await self.session.commit()
        await self.session.refresh(student)

        return {
            "student_id": str(student.id),
            "student_number": student.student_number,
            "user_id": str(user.id),
            "booking_id": str(booking.id),
            "booking_number": booking.booking_number,
            "full_name": user.full_name,
            "email": user.email,
            "room_id": str(student.room_id),
            "bed_id": str(student.bed_id),
            "check_in_date": str(student.check_in_date),
        }
    async def delete_room(self, room_id: str) -> None:
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found.")
        await self.repository.delete_room(room)
        await self.session.commit()