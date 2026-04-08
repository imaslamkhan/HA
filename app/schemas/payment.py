from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.base import APIModel


class BookingPaymentCreateRequest(BaseModel):
    booking_advance: float = Field(ge=0)
    payment_method: str = Field(default="razorpay", min_length=2, max_length=50)


class BookingPaymentOrderResponse(BaseModel):
    payment: "PaymentResponse"
    razorpay_order: dict


class RazorpayWebhookRequest(BaseModel):
    event: str
    payload: dict


class PaymentResponse(APIModel):
    id: str
    hostel_id: str
    student_id: str | None = None
    booking_id: str | None = None
    amount: float
    payment_type: str
    payment_method: str
    gateway_order_id: str | None = None
    gateway_payment_id: str | None = None
    gateway_signature: str | None = None
    status: str
    receipt_url: str | None = None
    due_date: date | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
