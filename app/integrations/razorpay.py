import hashlib
import hmac
import json

from app.config import get_settings


class RazorpayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret
        self.webhook_secret = settings.razorpay_webhook_secret or self.key_secret
        self._client = None

    def _get_client(self):
        if self._client is None:
            import razorpay
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        return self._client

    def create_order(self, *, amount: float, receipt: str, notes: dict | None = None) -> dict:
        amount_paise = int(round(amount * 100))
        order = self._get_client().order.create(data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
        })
        order["key_id"] = self.key_id
        return order

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        try:
            self._get_client().utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            return True
        except Exception:
            return False

    def verify_webhook_signature(self, payload_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"), payload_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_signature(self, payload: dict, signature: str | None) -> bool:
        if not signature:
            return False
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
