import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.payment import Payment, PaymentWebhookEvent


class PaymentWriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_booking_by_id(self, booking_id: str) -> Booking | None:
        result = await self.session.execute(select(Booking).where(Booking.id == booking_id))
        return result.scalar_one_or_none()

    async def create_payment(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_payment_by_gateway_order_id(self, gateway_order_id: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.gateway_order_id == gateway_order_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_gateway_payment_id(self, gateway_payment_id: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.gateway_payment_id == gateway_payment_id)
        )
        return result.scalar_one_or_none()

    async def create_webhook_event(
        self,
        *,
        provider: str,
        event_type: str,
        payload: dict,
        status: str,
        event_id: str | None = None,
    ) -> PaymentWebhookEvent:
        event = PaymentWebhookEvent(
            provider=provider,
            event_type=event_type,
            payload_json=json.dumps(payload, sort_keys=True),
            status=status,
            processed_at=datetime.now(UTC) if status != "received" else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event
    
    async def get_webhook_event_by_provider_id(self, *, provider: str, event_id: str) -> PaymentWebhookEvent | None:
        """
        Get webhook event by provider's event ID for idempotency check.
        
        This prevents processing the same webhook event multiple times.
        """
        # We need to extract event_id from payload_json since we don't store it separately
        # For better querying, consider adding a provider_event_id column
        result = await self.session.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.provider == provider,
                PaymentWebhookEvent.payload_json.contains(event_id)
            )
        )
        # Verify it's actually the right event type
        for event in result.scalars().all():
            import json as json_lib
            try:
                payload = json_lib.loads(event.payload_json)
                payload_block = payload.get("payload", {})
                payment_entity_id = payload_block.get("payment", {}).get("entity", {}).get("id")
                order_entity_id = payload_block.get("order", {}).get("entity", {}).get("id")
                entity_id = (
                    payment_entity_id or
                    order_entity_id or
                    payload.get("id")
                )
                if entity_id == event_id:
                    return event
            except Exception:
                continue
        return None
