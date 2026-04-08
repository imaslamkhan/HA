import json

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.dependencies import DBSession
from app.services.payment_write_service import PaymentWriteService

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: DBSession,
    x_razorpay_signature: str | None = Header(default=None),
):
    """
    **Razorpay payment webhook.**

    Called automatically by Razorpay after payment events.
    Do not call this manually in production.

    **Processing flow:**
    1. Verify HMAC-SHA256 signature using `RAZORPAY_WEBHOOK_SECRET`
    2. Check idempotency — skip if event already processed
    3. On `payment.captured` → mark payment as `captured`, move booking to `pending_approval`
    4. On `payment.failed` → mark payment as `failed` with error details
    5. Store raw event in `payment_webhook_events` for audit

    **Supported events:** `payment.captured`, `payment.failed`, `order.paid`
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload.",
        ) from exc

    return await PaymentWriteService(db).handle_razorpay_webhook(
        payload=payload,
        signature=x_razorpay_signature,
        raw_body=raw_body,
    )
