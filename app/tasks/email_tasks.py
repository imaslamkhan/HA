"""
Background email tasks using Celery.
"""
from app.celery_app import celery_app
from app.integrations.email import EmailService


@celery_app.task(bind=True, max_retries=3)
def send_booking_confirmation_task(
    self,
    recipient_email: str,
    recipient_name: str,
    booking_number: str,
    hostel_name: str,
    check_in_date: str,
    check_out_date: str,
    total_amount: float,
    payment_status: str
):
    """Send booking confirmation email as background task."""
    try:
        email_service = EmailService()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(email_service.send_booking_confirmation(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            booking_number=booking_number,
            hostel_name=hostel_name,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            total_amount=total_amount,
            payment_status=payment_status
        ))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_payment_receipt_task(
    self,
    recipient_email: str,
    recipient_name: str,
    payment_id: str,
    amount: float,
    payment_type: str,
    transaction_id: str,
    payment_date: str
):
    """Send payment receipt email as background task."""
    try:
        email_service = EmailService()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(email_service.send_payment_receipt(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            payment_id=payment_id,
            amount=amount,
            payment_type=payment_type,
            transaction_id=transaction_id,
            payment_date=payment_date
        ))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_otp_task(
    self,
    recipient_email: str,
    recipient_name: str,
    otp: str
):
    """Send password reset OTP email as background task."""
    try:
        email_service = EmailService()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(email_service.send_password_reset_otp(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            otp=otp
        ))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_registration_welcome_task(
    self,
    recipient_email: str,
    recipient_name: str
):
    """Send welcome email as background task."""
    try:
        email_service = EmailService()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(email_service.send_registration_welcome(
            recipient_email=recipient_email,
            recipient_name=recipient_name
        ))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
