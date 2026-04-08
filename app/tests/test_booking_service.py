"""
Tests for Booking Service - Critical Path Testing

These tests ensure booking integrity, overlap detection, and proper state transitions.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.services.booking_service import BookingService
from app.models.booking import Booking, BookingStatus, BedStayStatus, BookingMode
from app.models.user import User, UserRole


class TestBookingOverlapDetection:
    """Test suite for bed overlap detection - CRITICAL FOR PREVENTING DOUBLE BOOKINGS"""
    
    @pytest.mark.asyncio
    async def test_no_overlap_different_dates(self, session: AsyncSession, test_bed: str):
        """Test that bookings with non-overlapping dates are allowed"""
        from app.repositories.booking_repository import BookingRepository
        
        repo = BookingRepository(session)
        
        # Create initial booking: Jan 1-5
        has_overlap = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5)
        )
        assert has_overlap is False
        
        # Try booking after: Jan 6-10 (should not overlap)
        has_overlap_after = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2026, 1, 6),
            end_date=date(2026, 1, 10)
        )
        assert has_overlap_after is False
    
    @pytest.mark.asyncio
    async def test_overlap_partial(self, session: AsyncSession, test_bed: str, create_booking):
        """Test that partially overlapping dates are detected"""
        from app.repositories.booking_repository import BookingRepository
        
        # Create booking: Jan 1-5
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        repo = BookingRepository(session)
        
        # Try booking: Jan 3-7 (overlaps Jan 3-5)
        has_overlap = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2026, 1, 3),
            end_date=date(2026, 1, 7)
        )
        assert has_overlap is True
        
        # Try booking: Dec 28 - Jan 2 (overlaps Jan 1-2)
        has_overlap_before = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2025, 12, 28),
            end_date=date(2026, 1, 2)
        )
        assert has_overlap_before is True
    
    @pytest.mark.asyncio
    async def test_overlap_complete(self, session: AsyncSession, test_bed: str, create_booking):
        """Test that completely contained dates are detected"""
        from app.repositories.booking_repository import BookingRepository
        
        # Create booking: Jan 1-10
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 10),
            status=BookingStatus.APPROVED
        )
        
        repo = BookingRepository(session)
        
        # Try booking: Jan 3-7 (completely within existing booking)
        has_overlap = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2026, 1, 3),
            end_date=date(2026, 1, 7)
        )
        assert has_overlap is True
    
    @pytest.mark.asyncio
    async def test_exclude_self_on_update(self, session: AsyncSession, test_bed: str, create_booking):
        """Test that updating a booking doesn't conflict with itself"""
        from app.repositories.booking_repository import BookingRepository
        
        # Create booking: Jan 1-5
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        repo = BookingRepository(session)
        
        # Check overlap excluding self (should be False)
        has_overlap = await repo.has_overlap(
            bed_id=test_bed,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
            exclude_booking_id=str(booking.id)
        )
        assert has_overlap is False


class TestBookingCreation:
    """Test suite for booking creation flow"""
    
    @pytest.mark.asyncio
    async def test_create_booking_success(self, session: AsyncSession, test_visitor: User):
        """Test successful booking creation"""
        from app.schemas.booking import BookingCreateRequest, BookingModeEnum
        
        service = BookingService(session)
        
        request = BookingCreateRequest(
            hostel_id="test-hostel-id",
            room_id="test-room-id",
            booking_mode=BookingModeEnum.DAILY,
            check_in_date=date(2026, 1, 1),
            check_out_date=date(2026, 1, 5),
            full_name="Test Visitor",
            base_rent_amount=1000.0,
            security_deposit=500.0,
            booking_advance=1500.0,
        )
        
        booking = await service.create_booking(
            visitor_id=str(test_visitor.id),
            payload=request
        )
        
        assert booking is not None
        assert booking.status == BookingStatus.PAYMENT_PENDING
        assert booking.visitor_id == str(test_visitor.id)
        assert booking.booking_number.startswith("HB-")
    
    @pytest.mark.asyncio
    async def test_create_booking_monthly_mode(self, session: AsyncSession, test_visitor: User):
        """Test monthly booking creation calculates months correctly"""
        from app.schemas.booking import BookingCreateRequest, BookingModeEnum
        
        service = BookingService(session)
        
        # 3 month booking
        request = BookingCreateRequest(
            hostel_id="test-hostel-id",
            room_id="test-room-id",
            booking_mode=BookingModeEnum.MONTHLY,
            check_in_date=date(2026, 1, 1),
            check_out_date=date(2026, 4, 1),  # 3 months
            full_name="Test Visitor",
            base_rent_amount=9000.0,
            security_deposit=5000.0,
            booking_advance=14000.0,
        )
        
        booking = await service.create_booking(
            visitor_id=str(test_visitor.id),
            payload=request
        )
        
        assert booking.total_months == 3
        assert booking.total_nights is None


class TestBookingApproval:
    """Test suite for booking approval flow - CRITICAL"""
    
    @pytest.mark.asyncio
    async def test_approve_booking_creates_bed_stay(
        self, 
        session: AsyncSession, 
        create_booking,
        test_visitor: User,
        test_bed: str
    ):
        """Test that approving a booking creates a BedStay record"""
        from sqlalchemy import select
        from app.models.booking import BedStay
        
        # Create a pending booking
        booking = await create_booking(
            bed_id=None,  # No bed assigned yet
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.PAYMENT_PENDING
        )
        
        service = BookingService(session)
        
        # Approve with bed assignment
        approved_booking = await service.approve_booking(
            booking_id=str(booking.id),
            approved_by=str(test_visitor.id),
            bed_id=test_bed
        )
        
        assert approved_booking.status == BookingStatus.APPROVED
        assert approved_booking.bed_id == test_bed
        
        # Verify BedStay was created
        result = await session.execute(
            select(BedStay).where(
                BedStay.booking_id == str(booking.id),
                BedStay.bed_id == test_bed,
                BedStay.status == BedStayStatus.RESERVED
            )
        )
        bed_stay = result.scalar_one_or_none()
        assert bed_stay is not None
    
    @pytest.mark.asyncio
    async def test_approve_booking_fails_on_overlap(
        self,
        session: AsyncSession,
        create_booking,
        test_visitor: User,
        test_bed: str
    ):
        """Test that approving a booking fails if bed is already booked"""
        from fastapi import HTTPException
        
        # Create first booking (approved)
        booking1 = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        # Create second booking (pending) for same dates
        booking2 = await create_booking(
            bed_id=None,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.PENDING_APPROVAL
        )
        
        service = BookingService(session)
        
        # Try to approve second booking (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await service.approve_booking(
                booking_id=str(booking2.id),
                approved_by=str(test_visitor.id),
                bed_id=test_bed
            )
        
        assert exc_info.value.status_code == 409
        assert "not available" in str(exc_info.value.detail)


class TestBookingRejection:
    """Test suite for booking rejection flow"""
    
    @pytest.mark.asyncio
    async def test_reject_booking_releases_bed(
        self,
        session: AsyncSession,
        create_booking,
        test_visitor: User,
        test_bed: str
    ):
        """Test that rejecting a booking releases the reserved bed"""
        from sqlalchemy import select
        from app.models.booking import BedStay
        
        # Create approved booking with bed
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        # Verify BedStay exists
        result = await session.execute(
            select(BedStay).where(
                BedStay.booking_id == str(booking.id),
                BedStay.status == BedStayStatus.RESERVED
            )
        )
        bed_stay = result.scalar_one_or_none()
        assert bed_stay is not None
        
        service = BookingService(session)
        
        # Reject booking
        rejected = await service.reject_booking(
            booking_id=str(booking.id),
            rejected_by=str(test_visitor.id),
            reason="Test rejection"
        )
        
        assert rejected.status == BookingStatus.REJECTED
        assert rejected.rejection_reason == "Test rejection"
        
        # Verify BedStay was released (marked as CANCELLED)
        result = await session.execute(
            select(BedStay).where(
                BedStay.booking_id == str(booking.id),
                BedStay.status == BedStayStatus.CANCELLED
            )
        )
        cancelled_stay = result.scalar_one_or_none()
        assert cancelled_stay is not None


class TestCheckInCheckOut:
    """Test suite for student check-in/check-out flow"""
    
    @pytest.mark.asyncio
    async def test_check_in_updates_bed_stay_status(
        self,
        session: AsyncSession,
        create_booking,
        test_visitor: User,
        test_bed: str
    ):
        """Test that checking in updates BedStay from RESERVED to ACTIVE"""
        from sqlalchemy import select
        from app.models.booking import BedStay
        
        # Create approved booking
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        service = BookingService(session)
        
        # Check in
        checked_in = await service.check_in_student(
            booking_id=str(booking.id),
            checked_in_by=str(test_visitor.id)
        )
        
        assert checked_in.status == BookingStatus.CHECKED_IN
        
        # Verify BedStay status updated to ACTIVE
        result = await session.execute(
            select(BedStay).where(
                BedStay.booking_id == str(booking.id),
                BedStay.status == BedStayStatus.ACTIVE
            )
        )
        active_stay = result.scalar_one_or_none()
        assert active_stay is not None
    
    @pytest.mark.asyncio
    async def test_check_out_updates_bed_stay_to_completed(
        self,
        session: AsyncSession,
        create_booking,
        test_visitor: User,
        test_bed: str
    ):
        """Test that checking out updates BedStay from ACTIVE to COMPLETED"""
        from sqlalchemy import select
        from app.models.booking import BedStay
        
        # Create checked-in booking
        booking = await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.CHECKED_IN
        )
        
        service = BookingService(session)
        
        # Check out
        checked_out = await service.check_out_student(
            booking_id=str(booking.id),
            checked_out_by=str(test_visitor.id)
        )
        
        assert checked_out.status == BookingStatus.CHECKED_OUT
        
        # Verify BedStay status updated to COMPLETED
        result = await session.execute(
            select(BedStay).where(
                BedStay.booking_id == str(booking.id),
                BedStay.status == BedStayStatus.COMPLETED
            )
        )
        completed_stay = result.scalar_one_or_none()
        assert completed_stay is not None
    
    @pytest.mark.asyncio
    async def test_cannot_check_in_non_approved_booking(
        self,
        session: AsyncSession,
        create_booking,
        test_visitor: User
    ):
        """Test that checking in fails for non-approved bookings"""
        from fastapi import HTTPException
        
        # Create pending booking
        booking = await create_booking(
            bed_id=None,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.PENDING_APPROVAL
        )
        
        service = BookingService(session)
        
        # Try to check in (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await service.check_in_student(
                booking_id=str(booking.id),
                checked_in_by=str(test_visitor.id)
            )
        
        assert exc_info.value.status_code == 400
        assert "not APPROVED" in str(exc_info.value.detail)


class TestBedAvailability:
    """Test suite for bed availability queries"""
    
    @pytest.mark.asyncio
    async def test_get_available_beds(
        self,
        session: AsyncSession,
        create_multiple_beds,
        create_booking
    ):
        """Test getting all available beds for date range"""
        from app.repositories.booking_repository import BookingRepository
        
        # Create 3 beds
        beds = await create_multiple_beds(count=3)
        
        # Book 1 bed
        await create_booking(
            bed_id=str(beds[0].id),
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        repo = BookingRepository(session)
        
        # Get available beds for Jan 1-5
        available = await repo.get_available_beds(
            hostel_id="test-hostel-id",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5)
        )
        
        # Should have 2 available (beds 2 and 3)
        assert len(available) == 2
        assert str(beds[0].id) not in [str(b.id) for b in available]
    
    @pytest.mark.asyncio
    async def test_is_bed_available_helper(
        self,
        session: AsyncSession,
        test_bed: str,
        create_booking
    ):
        """Test the is_bed_available helper method"""
        from app.repositories.booking_repository import BookingRepository
        
        # Initially should be available
        repo = BookingRepository(session)
        available = await repo.is_bed_available(
            bed_id=test_bed,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5)
        )
        assert available is True
        
        # Book it
        await create_booking(
            bed_id=test_bed,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            status=BookingStatus.APPROVED
        )
        
        # Should not be available anymore
        available_after = await repo.is_bed_available(
            bed_id=test_bed,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5)
        )
        assert available_after is False
