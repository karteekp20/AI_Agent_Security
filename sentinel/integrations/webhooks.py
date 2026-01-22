from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
import hmac
import hashlib
import json
import asyncio
import httpx

from dataclasses import dataclass


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    webhook_id: UUID
    org_id: UUID
    url: str
    secret: str
    events: List[str]
    enabled: bool = True
    failure_count: int = 0
    max_retries: int = 3


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt"""
    delivery_id: UUID
    webhook_id: UUID
    event_type: str
    payload: Dict[str, Any]
    status: str  # pending, success, failed
    response_code: Optional[int]
    retry_count: int
    created_at: datetime
    delivered_at: Optional[datetime]


class WebhookService:
    """
    Webhook delivery service with retry and signing

    Features:
    - HMAC-SHA256 signing for payload verification
    - Exponential backoff retry
    - Dead letter queue for failed deliveries
    """

    # Event types
    EVENT_TYPES = [
        "threat.detected",
        "threat.blocked",
        "policy.created",
        "policy.updated",
        "policy.deployed",
        "anomaly.detected",
        "compliance.alert",
    ]

    def __init__(self, db=None, max_retries: int = 3):
        self.db = db
        self.max_retries = max_retries
        self._delivery_queue: asyncio.Queue = asyncio.Queue()

    def create_webhook(
        self,
        org_id: UUID,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> WebhookConfig:
        """
        Create a new webhook configuration

        Args:
            org_id: Organization owning the webhook
            url: Endpoint URL to deliver to
            events: List of event types to subscribe to
            secret: Optional secret for HMAC signing (generated if not provided)
        """
        # Validate events
        for event in events:
            if event not in self.EVENT_TYPES:
                raise ValueError(f"Unknown event type: {event}")

        # Generate secret if not provided
        if not secret:
            secret = self._generate_secret()

        config = WebhookConfig(
            webhook_id=uuid4(),
            org_id=org_id,
            url=url,
            secret=secret,
            events=events,
            enabled=True,
        )

        # Would save to database here
        return config

    async def trigger_event(
        self,
        org_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
    ) -> List[UUID]:
        """
        Trigger webhooks for an event

        Args:
            org_id: Organization the event belongs to
            event_type: Type of event
            payload: Event data

        Returns:
            List of delivery IDs for tracking
        """
        # Get all webhooks subscribed to this event for this org
        webhooks = self._get_webhooks_for_event(org_id, event_type)

        delivery_ids = []
        for webhook in webhooks:
            if not webhook.enabled:
                continue

            delivery = WebhookDelivery(
                delivery_id=uuid4(),
                webhook_id=webhook.webhook_id,
                event_type=event_type,
                payload=payload,
                status="pending",
                response_code=None,
                retry_count=0,
                created_at=datetime.utcnow(),
                delivered_at=None,
            )

            # Queue for delivery
            await self._delivery_queue.put((webhook, delivery))
            delivery_ids.append(delivery.delivery_id)

        return delivery_ids

    async def process_deliveries(self):
        """Background task to process webhook deliveries"""
        while True:
            try:
                webhook, delivery = await self._delivery_queue.get()
                await self._deliver(webhook, delivery)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing delivery: {e}")

    async def _deliver(
        self,
        webhook: WebhookConfig,
        delivery: WebhookDelivery,
    ) -> bool:
        """
        Deliver a webhook with retry logic
        """
        payload_json = json.dumps(delivery.payload, default=str)

        # Sign the payload
        signature = self._sign_payload(payload_json, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Sentinel-Signature": signature,
            "X-Sentinel-Event": delivery.event_type,
            "X-Sentinel-Delivery-ID": str(delivery.delivery_id),
            "X-Sentinel-Timestamp": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient() as client:
            while delivery.retry_count <= self.max_retries:
                try:
                    response = await client.post(
                        webhook.url,
                        content=payload_json,
                        headers=headers,
                        timeout=30.0,
                    )

                    delivery.response_code = response.status_code

                    if response.status_code < 300:
                        delivery.status = "success"
                        delivery.delivered_at = datetime.utcnow()
                        # Save delivery record
                        return True

                    # Non-success response
                    delivery.retry_count += 1

                except Exception as e:
                    print(f"Webhook delivery failed: {e}")
                    delivery.retry_count += 1

                # Exponential backoff
                if delivery.retry_count <= self.max_retries:
                    backoff = 2 ** delivery.retry_count
                    await asyncio.sleep(backoff)

        # All retries exhausted
        delivery.status = "failed"
        webhook.failure_count += 1

        # Disable webhook if too many failures
        if webhook.failure_count >= 10:
            webhook.enabled = False

        return False

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def _generate_secret(self) -> str:
        """Generate a random webhook secret"""
        import secrets
        return secrets.token_hex(32)

    def _get_webhooks_for_event(
        self,
        org_id: UUID,
        event_type: str
    ) -> List[WebhookConfig]:
        """Get webhooks subscribed to an event"""
        if self.db is None:
            return []

        try:
            from sentinel.saas.models.webhook import Webhook

            # Query webhooks for this org that are enabled and subscribed to this event
            webhooks = self.db.query(Webhook).filter(
                Webhook.org_id == org_id,
                Webhook.enabled == True,
                Webhook.events.contains([event_type])
            ).all()

            return [
                WebhookConfig(
                    webhook_id=w.webhook_id,
                    org_id=w.org_id,
                    url=w.webhook_url,
                    secret=w.webhook_secret or "",
                    events=w.events or [],
                    enabled=w.enabled,
                    failure_count=w.failure_count or 0,
                )
                for w in webhooks
            ]
        except Exception as e:
            print(f"Error fetching webhooks: {e}")
            return []

    @staticmethod
    def verify_signature(
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature (for webhook receivers)

        Consumers of webhooks can use this to verify authenticity
        """
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)