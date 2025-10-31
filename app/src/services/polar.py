import logging
from typing import Any, Dict, Optional

import logfire
from fastapi import HTTPException
from polar_sdk import Polar, models
from polar_sdk.webhooks import WebhookVerificationError, validate_event

from src.core.config import settings

logger = logging.getLogger(__name__)


class PolarService:
    def __init__(self):
        access_token = settings.POLAR_ACCESS_TOKEN
        environment = settings.POLAR_ENVIRONMENT
        if environment.strip() == "":
            environment = "sandbox"
        self.client = Polar(access_token=access_token, server=environment)

    def validate_webhook_event(
        self, payload: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate and parse Polar webhook event using the official SDK.

        Args:
            payload: Raw webhook request body
            headers: Request headers containing webhook signature

        Returns:
            Parsed and validated webhook event data

        Raises:
            HTTPException: If signature is invalid or secret is not configured
        """
        with logfire.span("polar.validate_webhook_event"):
            if not settings.POLAR_WEBHOOK_SECRET:
                logger.error("POLAR_WEBHOOK_SECRET not configured")
                logfire.error("POLAR_WEBHOOK_SECRET not configured")
                raise HTTPException(
                    status_code=500, detail="Webhook secret not configured"
                )

            try:
                # Use Polar SDK's built-in webhook validation
                event = validate_event(
                    payload=payload,
                    headers=headers,
                    secret=settings.POLAR_WEBHOOK_SECRET,
                )

                logfire.info(
                    "Polar webhook validated successfully", event_type=event.get("type")
                )
                return event

            except WebhookVerificationError as e:
                logger.error(f"Webhook signature verification failed: {e}")
                logfire.error("Invalid Polar webhook signature", error=str(e))
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

    async def create_customer(
        self, email: str, external_customer_id: str
    ) -> Optional[str]:
        """
        Create a customer in Polar with external customer ID.

        Args:
            email: Customer email
            external_customer_id: External customer ID (Klyne user ID)

        Returns:
            Polar customer ID if successful, None if failed
        """
        with logfire.span(
            "polar.create_customer",
            external_customer_id=external_customer_id,
            email=email,
        ):
            try:
                customer_data = models.CustomerCreate(
                    email=email, external_id=external_customer_id
                )

                response = self.client.customers.create(request=customer_data)

                logger.info(
                    f"Created Polar customer for external ID {external_customer_id}"
                )
                logfire.info(
                    "Polar customer created successfully", customer_id=response.id
                )
                return response.id

            except models.PolarError as e:
                logger.error(f"Failed to create Polar customer: {e}")
                logfire.error("Failed to create Polar customer", error=str(e))
                return None
            except Exception as e:
                logger.error(f"Unexpected error creating Polar customer: {e}")
                logfire.error("Unexpected error creating Polar customer", error=str(e))
                return None

    async def create_checkout_session(
        self,
        product_id: str,
        external_customer_id: str,
        success_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a checkout session in Polar.

        Args:
            product_id: Polar product ID
            external_customer_id: External customer ID (Klyne user ID)
            success_url: URL to redirect after successful payment

        Returns:
            Checkout URL if successful, None if failed
        """
        with logfire.span(
            "polar.create_checkout_session",
            product_id=product_id,
            external_customer_id=external_customer_id,
        ):
            try:
                checkout_data = models.CheckoutCreate(
                    products=[product_id],
                    external_customer_id=external_customer_id,
                    success_url=success_url or f"{settings.APP_DOMAIN}/dashboard",
                )

                response = self.client.checkouts.create(request=checkout_data)

                logger.info(
                    f"Created checkout session for external customer {external_customer_id}"
                )
                logfire.info(
                    "Polar checkout session created successfully",
                    checkout_url=response.url,
                )
                return response.url

            except models.PolarError as e:
                logger.error(f"Failed to create checkout session: {e}")
                logfire.error("Failed to create Polar checkout session", error=str(e))
                return None
            except Exception as e:
                logger.error(f"Unexpected error creating checkout session: {e}")
                logfire.error(
                    "Unexpected error creating Polar checkout session", error=str(e)
                )
                return None

    async def get_customer_subscriptions(
        self, external_customer_id: str
    ) -> Dict[str, Any]:
        """
        Get customer subscriptions by external customer ID.

        Args:
            external_customer_id: External customer ID (Klyne user ID)

        Returns:
            Dictionary containing subscription status and details
        """
        with logfire.span(
            "polar.get_customer_subscriptions",
            external_customer_id=external_customer_id,
        ):
            try:
                # Get customer by external ID first
                customer = self.client.customers.get_external(
                    external_id=external_customer_id,
                )

                if not customer:
                    logfire.info(
                        "Polar customer not found",
                        external_customer_id=external_customer_id,
                    )
                    return {"active": False, "subscriptions": []}

                # Get customer subscriptions
                subscriptions = self.client.subscriptions.list(customer_id=customer.id)

                if not subscriptions:
                    logfire.info(
                        "No Polar subscriptions found", customer_id=customer.id
                    )
                    return {"active": False, "subscriptions": []}

                active_subscriptions = [
                    sub for sub in subscriptions.result.items if sub.status == "active"
                ]

                result = {
                    "active": len(active_subscriptions) > 0,
                    "subscriptions": active_subscriptions,
                }

                logfire.info(
                    "Polar subscriptions retrieved",
                    customer_id=customer.id,
                    active_count=len(active_subscriptions),
                    total_count=len(subscriptions.result.items),
                )

                return result

            except models.PolarError as e:
                logger.error(f"Failed to get customer subscriptions: {e}")
                logfire.error(
                    "Failed to get Polar customer subscriptions", error=str(e)
                )
                return {"active": False, "subscriptions": []}
            except Exception as e:
                logger.error(f"Unexpected error getting customer subscriptions: {e}")
                logfire.error(
                    "Unexpected error getting Polar customer subscriptions",
                    error=str(e),
                )
                return {"active": False, "subscriptions": []}

    async def get_customer_portal_url(self, external_customer_id: str) -> Optional[str]:
        """
        Get the customer portal URL for managing subscriptions.

        Args:
            external_customer_id: External customer ID (Klyne user ID)

        Returns:
            Customer portal URL if successful, None if failed
        """
        with logfire.span(
            "polar.get_customer_portal_url", external_customer_id=external_customer_id
        ):
            try:
                # Create customer portal session
                portal_session = self.client.customer_sessions.create(
                    request={"external_customer_id": external_customer_id}
                )

                logger.info(
                    f"Created customer portal session for external customer {external_customer_id}"
                )
                logfire.info(
                    "Polar customer portal session created successfully",
                    portal_url=portal_session.customer_portal_url,
                )
                return portal_session.customer_portal_url

            except models.PolarError as e:
                logger.error(f"Failed to create customer portal session: {e}")
                logfire.error(
                    "Failed to create Polar customer portal session", error=str(e)
                )
                return None
            except Exception as e:
                logger.error(f"Unexpected error creating customer portal session: {e}")
                logfire.error(
                    "Unexpected error creating Polar customer portal session",
                    error=str(e),
                )
                return None

    async def ingest_event(
        self, event_name: str, external_customer_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Ingest an event to Polar for analytics/billing.

        Args:
            event_name: Name of the event (e.g., "packages")
            external_customer_id: External customer ID (Klyne user ID)
            metadata: Event metadata dictionary

        Returns:
            True if successful, False if failed
        """
        with logfire.span(
            "polar.ingest_event",
            event_name=event_name,
            external_customer_id=external_customer_id,
            metadata=metadata,
        ):
            try:
                event_data = models.EventsIngest(
                    events=[
                        {
                            "name": event_name,
                            "external_customer_id": external_customer_id,
                            "metadata": metadata,
                        }
                    ]
                )

                self.client.events.ingest(request=event_data)

                logger.info(
                    f"Ingested event '{event_name}' for external customer {external_customer_id}"
                )
                logfire.info(
                    "Polar event ingested successfully",
                    event_name=event_name,
                    metadata=metadata,
                )
                return True

            except models.PolarError as e:
                logger.error(f"Failed to ingest event '{event_name}': {e}")
                logfire.error(
                    "Failed to ingest Polar event", event_name=event_name, error=str(e)
                )
                return False
            except Exception as e:
                logger.error(f"Unexpected error ingesting event '{event_name}': {e}")
                logfire.error(
                    "Unexpected error ingesting Polar event",
                    event_name=event_name,
                    error=str(e),
                )
                return False


# Global instance
polar_service = PolarService()
