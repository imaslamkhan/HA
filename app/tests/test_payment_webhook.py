"""
Tests for Payment Webhook Service - CRITICAL FOR PAYMENT SECURITY

These tests ensure:
1. Webhook signature verification works correctly
2. Idempotency prevents duplicate processing
3. Payment-booking synchronization is accurate
4. Error handling is robust
"""

import pytest
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.services.payment_write_service import PaymentWriteService
from app.models.payment import Payment, PaymentWebhookEvent
from app.models.booking import Booking, BookingStatus


class TestWebhookSignatureVerification:
    """Test suite for webhook signature verification - CRITICAL SECURITY"""
    
    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self, session: AsyncSession):
        """Test that valid signatures are accepted"""
        service = PaymentWriteService(session)
        
        # Simulate Razorpay webhook payload
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test123",
                        "order_id": "order_test123",
                        "amount": 150000,  # In paise
                        "currency": "INR",
                        "created_at": int(datetime.now().timestamp())
                    }
                }
            }
        }
        
        # Generate valid signature (in real scenario, this comes from Razorpay)
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Should not raise exception
        result = await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        assert result["received"] is True
        assert result["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, session: AsyncSession):
        """Test that invalid signatures are rejected"""
        service = PaymentWriteService(session)
        
        payload = {"event": "payment.captured"}
        invalid_signature = "invalid_signature_here"
        
        # Should raise 401 Unauthorized
        with pytest.raises(HTTPException) as exc_info:
            await service.handle_razorpay_webhook(
                payload=payload,
                signature=invalid_signature
            )
        
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in str(exc_info.value.detail)


class TestIdempotency:
    """Test suite for idempotent webhook processing - PREVENTS DUPLICATE CHARGES"""
    
    @pytest.mark.asyncio
    async def test_duplicate_webhook_not_processed_twice(
        self, 
        session: AsyncSession,
        create_payment
    ):
        """Test that same webhook event is not processed twice"""
        # Create a payment record
        payment = await create_payment(
            amount=1500.0,
            gateway_order_id="order_test123",
            status="pending"
        )
        
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_unique123",
                        "order_id": "order_test123",
                        "amount": 150000,
                        "created_at": int(datetime.now().timestamp())
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Process first time
        result1 = await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        assert result1["status"] == "processed"
        
        # Process same event second time (duplicate webhook)
        result2 = await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Should be marked as already processed
        assert result2["status"] == "already_processed"
        
        # Verify payment was only updated once
        from sqlalchemy import select
        result = await session.execute(
            select(Payment).where(Payment.gateway_order_id == "order_test123")
        )
        updated_payment = result.scalar_one_or_none()
        assert updated_payment.status == "captured"


class TestPaymentCapturedHandler:
    """Test suite for payment.captured event handling"""
    
    @pytest.mark.asyncio
    async def test_payment_captured_updates_status(
        self,
        session: AsyncSession,
        create_payment
    ):
        """Test that payment.captured updates payment status to 'captured'"""
        payment = await create_payment(
            amount=1500.0,
            gateway_order_id="order_test456",
            status="pending"
        )
        
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test456",
                        "order_id": "order_test456",
                        "amount": 150000,  # 1500 INR in paise
                        "created_at": int(datetime.now().timestamp())
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Verify payment status updated
        from sqlalchemy import select
        result = await session.execute(
            select(Payment).where(Payment.gateway_order_id == "order_test456")
        )
        updated_payment = result.scalar_one_or_none()
        
        assert updated_payment.status == "captured"
        assert updated_payment.gateway_payment_id == "pay_test456"
        assert updated_payment.paid_at is not None
    
    @pytest.mark.asyncio
    async def test_payment_captured_creates_missing_payment(
        self,
        session: AsyncSession
    ):
        """Test that webhook creates payment if it doesn't exist (race condition handling)"""
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_new789",
                        "order_id": "order_new789",
                        "amount": 200000,  # 2000 INR
                        "created_at": int(datetime.now().timestamp())
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Verify payment was created
        from sqlalchemy import select
        result = await session.execute(
            select(Payment).where(Payment.gateway_order_id == "order_new789")
        )
        created_payment = result.scalar_one_or_none()
        
        assert created_payment is not None
        assert created_payment.status == "captured"
        assert created_payment.amount == 2000.0  # Converted from paise


class TestBookingStatusSync:
    """Test suite for booking-payment synchronization"""
    
    @pytest.mark.asyncio
    async def test_payment_success_updates_booking_status(
        self,
        session: AsyncSession,
        create_booking_with_payment
    ):
        """Test that successful payment moves booking from PAYMENT_PENDING to PENDING_APPROVAL"""
        # Create booking with pending payment
        booking = await create_booking_with_payment(
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            booking_status=BookingStatus.PAYMENT_PENDING,
            payment_status="pending",
            amount=1500.0
        )
        
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_booking123",
                        "order_id": f"order_{booking.id}",
                        "amount": 150000,
                        "created_at": int(datetime.now().timestamp())
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Verify booking status updated
        from sqlalchemy import select
        result = await session.execute(
            select(Booking).where(Booking.id == str(booking.id))
        )
        updated_booking = result.scalar_one_or_none()
        
        assert updated_booking.status == BookingStatus.PENDING_APPROVAL
        
        # Verify status history was logged
        from app.models.booking import BookingStatusHistory
        history_result = await session.execute(
            select(BookingStatusHistory).where(
                BookingStatusHistory.booking_id == str(booking.id)
            )
        )
        history_records = list(history_result.scalars().all())
        
        assert len(history_records) >= 1
        assert any(
            h.new_status == BookingStatus.PENDING_APPROVAL and
            h.old_status == BookingStatus.PAYMENT_PENDING
            for h in history_records
        )


class TestPaymentFailedHandler:
    """Test suite for payment.failed event handling"""
    
    @pytest.mark.asyncio
    async def test_payment_failed_updates_status(
        self,
        session: AsyncSession,
        create_payment
    ):
        """Test that payment.failed marks payment as failed"""
        payment = await create_payment(
            amount=1500.0,
            gateway_order_id="order_fail123",
            status="pending"
        )
        
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail123",
                        "order_id": "order_fail123",
                        "failure_reason": "Insufficient funds",
                        "failure_code": "BAD_REQUEST"
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Verify payment status updated
        from sqlalchemy import select
        result = await session.execute(
            select(Payment).where(Payment.gateway_order_id == "order_fail123")
        )
        updated_payment = result.scalar_one_or_none()
        
        assert updated_payment.status == "failed"
        assert updated_payment.failure_reason == "Insufficient funds"
        assert updated_payment.failure_code == "BAD_REQUEST"


class TestWebhookEventLogging:
    """Test suite for webhook event audit logging"""
    
    @pytest.mark.asyncio
    async def test_webhook_event_persisted(self, session: AsyncSession):
        """Test that webhook events are persisted for audit"""
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_audit123",
                        "order_id": "order_audit123"
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        # Verify webhook event was logged
        result = await session.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.event_type == "payment.captured"
            )
        )
        events = list(result.scalars().all())
        
        assert len(events) >= 1
        assert events[-1].status == "processed"
        assert "pay_audit123" in events[-1].payload_json


class TestEdgeCases:
    """Test suite for edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_webhook_without_order_id_handled_gracefully(
        self,
        session: AsyncSession
    ):
        """Test that webhooks without order_id don't crash the system"""
        service = PaymentWriteService(session)
        
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_noorder123"
                        # Missing order_id
                    }
                }
            }
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Should raise HTTP 400 but not crash
        with pytest.raises(HTTPException) as exc_info:
            await service.handle_razorpay_webhook(
                payload=payload,
                signature=signature
            )
        
        assert exc_info.value.status_code == 400
        assert "Order ID missing" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_unknown_event_type_logged_but_not_failed(
        self,
        session: AsyncSession
    ):
        """Test that unknown event types are handled gracefully"""
        service = PaymentWriteService(session)
        
        payload = {
            "event": "unknown.event.type",
            "payload": {}
        }
        
        import json
        import hmac
        import hashlib
        
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            service.razorpay.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Should not fail
        result = await service.handle_razorpay_webhook(
            payload=payload,
            signature=signature
        )
        
        assert result["received"] is True
        assert result["event"] == "unknown.event.type"


# Helper fixtures (these would be in conftest.py in real project)

@pytest.fixture
def create_payment(session: AsyncSession):
    """Helper to create payment records for testing"""
    async def _create(amount: float, gateway_order_id: str, status: str):
        payment = Payment(
            hostel_id="test-hostel",
            booking_id=None,
            amount=amount,
            payment_type="booking_advance",
            payment_method="razorpay",
            gateway_order_id=gateway_order_id,
            status=status
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment
    return _create


@pytest.fixture
def create_booking_with_payment(session: AsyncSession):
    """Helper to create booking with payment for testing"""
    async def _create(check_in, check_out, booking_status, payment_status, amount):
        from app.models.booking import Booking
        from app.models.user import User, UserRole
        
        # Create visitor user
        visitor = User(
            email=f"test_{datetime.now().timestamp()}@test.com",
            phone=f"9999999999",
            full_name="Test Visitor",
            password_hash="hashed_pwd",
            role=UserRole.VISITOR
        )
        session.add(visitor)
        await session.flush()
        
        # Create booking
        booking = Booking(
            booking_number=f"HB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            visitor_id=str(visitor.id),
            hostel_id="test-hostel",
            room_id="test-room",
            booking_mode="daily",
            status=booking_status,
            check_in_date=check_in,
            check_out_date=check_out,
            base_rent_amount=amount,
            security_deposit=0,
            booking_advance=amount,
            grand_total=amount,
            full_name="Test Visitor"
        )
        session.add(booking)
        await session.flush()
        
        # Create payment
        payment = Payment(
            hostel_id="test-hostel",
            booking_id=str(booking.id),
            amount=amount,
            payment_type="booking_advance",
            payment_method="razorpay",
            gateway_order_id=f"order_{booking.id}",
            status=payment_status
        )
        session.add(payment)
        await session.commit()
        await session.refresh(booking)
        return booking
    return _create
