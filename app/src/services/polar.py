import logging
from typing import Any, Dict, Optional

from polar_sdk import Polar, models

from src.core.config import settings

logger = logging.getLogger(__name__)


class PolarService:
    def __init__(self):
        access_token = settings.POLAR_ACCESS_TOKEN
        environment = settings.POLAR_ENVIRONMENT
        if environment.strip() == "":
            environment = "sandbox"
        self.client = Polar(access_token=access_token, server=environment)

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
        try:
            customer_data = models.CustomerCreate(
                email=email, external_id=external_customer_id
            )

            response = self.client.customers.create(request=customer_data)

            logger.info(
                f"Created Polar customer for external ID {external_customer_id}"
            )
            return response.id

        except models.PolarError as e:
            logger.error(f"Failed to create Polar customer: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Polar customer: {e}")
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
            return response.url

        except models.PolarError as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {e}")
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
        try:
            # Get customer by external ID first
            customer = self.client.customers.get_external(
                external_id=external_customer_id,
            )

            if not customer:
                return {"active": False, "subscriptions": []}

            # Get customer subscriptions
            subscriptions = self.client.subscriptions.list(customer_id=customer.id)

            if not subscriptions:
                return {"active": False, "subscriptions": []}

            active_subscriptions = [
                sub for sub in subscriptions.result.items if sub.status == "active"
            ]

            return {
                "active": len(active_subscriptions) > 0,
                "subscriptions": active_subscriptions,
            }

        except models.PolarError as e:
            logger.error(f"Failed to get customer subscriptions: {e}")
            return {"active": False, "subscriptions": []}
        except Exception as e:
            logger.error(f"Unexpected error getting customer subscriptions: {e}")
            return {"active": False, "subscriptions": []}

    async def get_customer_portal_url(self, external_customer_id: str) -> Optional[str]:
        """
        Get the customer portal URL for managing subscriptions.

        Args:
            external_customer_id: External customer ID (Klyne user ID)

        Returns:
            Customer portal URL if successful, None if failed
        """
        try:
            # Create customer portal session
            portal_session = self.client.customer_sessions.create(
                request={"external_customer_id": external_customer_id}
            )

            logger.info(
                f"Created customer portal session for external customer {external_customer_id}"
            )
            return portal_session.customer_portal_url

        except models.PolarError as e:
            logger.error(f"Failed to create customer portal session: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating customer portal session: {e}")
            return None

    async def ingest_event(
        self, 
        event_name: str, 
        external_customer_id: str, 
        metadata: Dict[str, Any]
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
        try:
            event_data = models.EventsIngest(
                events=[{
                    "name": event_name,
                    "external_customer_id": external_customer_id,
                    "metadata": metadata
                }]
            )

            self.client.events.ingest(request=event_data)

            logger.info(
                f"Ingested event '{event_name}' for external customer {external_customer_id}"
            )
            return True

        except models.PolarError as e:
            logger.error(f"Failed to ingest event '{event_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error ingesting event '{event_name}': {e}")
            return False


# Global instance
polar_service = PolarService()
