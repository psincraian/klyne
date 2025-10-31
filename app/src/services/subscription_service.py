import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import logfire
from fastapi import HTTPException

from src.core.config import settings
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork
from src.services.polar import PolarService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription-related business logic."""

    def __init__(
        self, uow: AbstractUnitOfWork, polar_service: Optional[PolarService] = None
    ):
        self.uow = uow
        self.polar_service = polar_service

    async def get_user_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive subscription status for a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription_info = {
            "user_id": user_id,
            "subscription_tier": user.subscription_tier,
            "subscription_status": user.subscription_status,
            "subscription_updated_at": user.subscription_updated_at,
            "is_active": user.subscription_status == "active",
            "has_subscription": user.subscription_tier is not None,
        }

        # If Polar service is available, get additional details
        if self.polar_service:
            try:
                polar_subscription = (
                    await self.polar_service.get_customer_subscriptions(str(user_id))
                )
                subscription_info.update(
                    {
                        "polar_active": polar_subscription.get("active", False),
                        "polar_subscriptions": polar_subscription.get(
                            "subscriptions", []
                        ),
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get Polar subscription info for user {user_id}: {e}"
                )

        return subscription_info

    async def update_subscription_from_polar(self, user_id: int) -> User:
        """Update user subscription status by syncing with Polar."""
        if not self.polar_service:
            raise HTTPException(status_code=500, detail="Polar service not available")

        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            # Get subscription from Polar
            polar_subscription = await self.polar_service.get_customer_subscriptions(
                str(user_id)
            )

            if polar_subscription["active"]:
                # Determine subscription tier from Polar data
                subscriptions = polar_subscription.get("subscriptions", [])
                if subscriptions:
                    # For now, just mark as active - you could parse product info for tier
                    subscription_tier = "pro"  # Default or parse from subscription data
                    subscription_status = "active"
                else:
                    subscription_tier = None
                    subscription_status = None
            else:
                subscription_tier = None
                subscription_status = "canceled"

            # Update user subscription
            updated_user = await self.uow.users.update_subscription(
                user_id=user_id,
                subscription_tier=subscription_tier,
                subscription_status=subscription_status,
                subscription_updated_at=datetime.now(timezone.utc),
            )

            await self.uow.commit()
            logger.info(
                f"Updated subscription for user {user.email} from Polar: {subscription_tier} - {subscription_status}"
            )
            return updated_user

        except Exception as e:
            logger.error(
                f"Failed to sync subscription from Polar for user {user_id}: {e}"
            )
            raise HTTPException(
                status_code=500, detail="Failed to sync subscription status"
            )

    async def activate_subscription(
        self, user_id: int, subscription_tier: str = "pro"
    ) -> User:
        """Activate a subscription for a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updated_user = await self.uow.users.update_subscription(
            user_id=user_id,
            subscription_tier=subscription_tier,
            subscription_status="active",
            subscription_updated_at=datetime.now(timezone.utc),
        )

        await self.uow.commit()
        logger.info(f"Activated {subscription_tier} subscription for user {user.email}")
        return updated_user

    async def cancel_subscription(self, user_id: int) -> User:
        """Cancel a user's subscription."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updated_user = await self.uow.users.update_subscription(
            user_id=user_id,
            subscription_tier=user.subscription_tier,  # Keep the tier but change status
            subscription_status="canceled",
            subscription_updated_at=datetime.now(timezone.utc),
        )

        await self.uow.commit()
        logger.info(f"Canceled subscription for user {user.email}")
        return updated_user

    async def has_active_subscription(self, user_id: int) -> bool:
        """Check if user has an active subscription."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return False

        return (
            user.subscription_status == "active" and user.is_active and user.is_verified
        )

    async def require_active_subscription(self, user_id: int) -> User:
        """Require user to have an active subscription, raise exception if not."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email verification required")

        if user.subscription_status != "active":
            raise HTTPException(status_code=403, detail="Active subscription required")

        return user

    async def get_subscription_limits(self, user_id: int) -> Dict[str, Any]:
        """Get subscription limits for a user based on their tier."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Define limits based on subscription tier
        if user.subscription_tier == "free":
            limits = {
                "max_api_keys": 1,
                "max_events_per_month": 3000,  # ~100/hour * 24 * 30
                "max_packages": 1,
                "data_retention_days": 7,
                "features": ["basic_analytics", "7_day_retention"],
            }
        elif user.subscription_tier == "starter":
            limits = {
                "max_api_keys": 1,
                "max_events_per_month": 10000,
                "max_packages": 1,
                "data_retention_days": -1,  # Unlimited
                "features": ["basic_analytics", "unlimited_retention", "email_support"],
            }
        elif user.subscription_tier == "pro":
            limits = {
                "max_api_keys": 10,
                "max_events_per_month": 100000,
                "max_packages": 10,
                "data_retention_days": -1,  # Unlimited
                "features": [
                    "advanced_analytics",
                    "unlimited_retention",
                    "priority_support",
                    "custom_alerts",
                ],
            }
        else:
            # No subscription
            limits = {
                "max_api_keys": 0,
                "max_events_per_month": 0,
                "max_packages": 0,
                "data_retention_days": 0,
                "features": [],
            }

        return {
            "user_id": user_id,
            "subscription_tier": user.subscription_tier,
            "subscription_status": user.subscription_status,
            "limits": limits,
        }

    async def check_usage_limits(self, user_id: int) -> Dict[str, Any]:
        """Check current usage against subscription limits."""
        limits = await self.get_subscription_limits(user_id)

        # Get current usage
        api_key_count = await self.uow.api_keys.count_active_keys_by_user(user_id)
        package_count = len(await self.uow.api_keys.get_packages_for_user(user_id))

        # Calculate usage percentages
        max_api_keys = limits["limits"]["max_api_keys"]
        max_packages = limits["limits"]["max_packages"]

        usage = {
            "api_keys": {
                "current": api_key_count,
                "limit": max_api_keys,
                "percentage": (api_key_count / max_api_keys * 100)
                if max_api_keys > 0
                else 0,
            },
            "packages": {
                "current": package_count,
                "limit": max_packages,
                "percentage": (package_count / max_packages * 100)
                if max_packages > 0
                else 0,
            },
        }

        return {
            "user_id": user_id,
            "subscription_tier": limits["subscription_tier"],
            "usage": usage,
            "limits": limits["limits"],
        }

    async def can_create_api_key(self, user_id: int) -> bool:
        """Check if user can create another API key."""
        if not await self.has_active_subscription(user_id):
            return False

        limits = await self.get_subscription_limits(user_id)
        current_count = await self.uow.api_keys.count_active_keys_by_user(user_id)

        return current_count < limits["limits"]["max_api_keys"]

    async def create_polar_customer(self, user_id: int) -> Optional[str]:
        """Create a customer in Polar for the user."""
        if not self.polar_service:
            logger.warning("Polar service not available")
            return None

        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            polar_customer_id = await self.polar_service.create_customer(
                email=user.email, external_customer_id=str(user_id)
            )

            if polar_customer_id:
                logger.info(
                    f"Created Polar customer for user {user.email}: {polar_customer_id}"
                )

            return polar_customer_id

        except Exception as e:
            logger.error(f"Failed to create Polar customer for user {user_id}: {e}")
            return None

    async def create_checkout_session(
        self, user_id: int, product_id: str, success_url: Optional[str] = None
    ) -> Optional[str]:
        """Create a checkout session for the user."""
        if not self.polar_service:
            raise HTTPException(status_code=500, detail="Polar service not available")

        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            checkout_url = await self.polar_service.create_checkout_session(
                product_id=product_id,
                external_customer_id=str(user_id),
                success_url=success_url,
            )

            if checkout_url:
                logger.info(f"Created checkout session for user {user.email}")

            return checkout_url

        except Exception as e:
            logger.error(f"Failed to create checkout session for user {user_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to create checkout session"
            )

    async def has_any_subscription(self, user_id: int) -> bool:
        """Check if user has ever had any subscription (active or inactive)."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return False

        return user.subscription_tier is not None

    async def is_subscription_expired(self, user_id: int) -> bool:
        """Check if user had a subscription that is now expired/canceled."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return False

        return (
            user.subscription_tier is not None and user.subscription_status != "active"
        )

    async def get_subscription_message_for_user(self, user_id: int) -> Dict[str, Any]:
        """Get appropriate subscription message and CTA for user based on their status."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return {
                "title": "Account Error",
                "message": "User not found",
                "cta_text": "Contact Support",
                "cta_url": "/support",
            }

        has_any = await self.has_any_subscription(user_id)
        is_active = await self.has_active_subscription(user_id)

        if is_active:
            return {
                "title": "Active Subscription",
                "message": f"You have an active {user.subscription_tier.title()} subscription",
                "cta_text": "Manage Subscription",
                "cta_url": "/pricing",
            }
        elif has_any:
            return {
                "title": "Subscription Expired",
                "message": "Your subscription has expired. Reactivate to continue using Klyne analytics.",
                "cta_text": "Reactivate Subscription",
                "cta_url": "/pricing",
            }
        else:
            return {
                "title": "Subscription Required",
                "message": "Get started with package analytics by choosing a subscription plan that fits your needs.",
                "cta_text": "View Pricing Plans",
                "cta_url": "/pricing",
            }

    async def process_webhook_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Process Polar webhook events and update user subscriptions.

        Args:
            event_type: Type of webhook event (e.g., 'subscription.active', 'subscription.canceled')
            event_data: Event data payload from Polar

        Returns:
            Dictionary with status message

        Raises:
            HTTPException: If event processing fails
        """
        with logfire.span("subscription.process_webhook_event", event_type=event_type):
            # Only handle subscription events we care about
            if event_type not in ["subscription.active", "subscription.canceled"]:
                logger.info(f"Ignoring webhook event type: {event_type}")
                logfire.info("Ignoring Polar webhook event", event_type=event_type)
                return {
                    "status": "ignored",
                    "message": f"Event type '{event_type}' not handled",
                }

            # Get external customer ID from the subscription
            external_customer_id = event_data.get("customer", {}).get("external_id")
            if not external_customer_id:
                logger.error("No external_customer_id found in webhook payload")
                logfire.error(
                    "Missing external_customer_id in Polar webhook",
                    event_data=event_data,
                )
                raise HTTPException(
                    status_code=400, detail="Missing external_customer_id"
                )

            # Find the user by external customer ID (user.id)
            try:
                user_id = int(external_customer_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid external_customer_id: {external_customer_id}")
                logfire.error(
                    "Invalid external_customer_id",
                    external_customer_id=external_customer_id,
                )
                raise HTTPException(
                    status_code=400, detail="Invalid external_customer_id"
                )

            user = await self.uow.users.get_by_id(user_id)
            if not user:
                logger.error(
                    f"User not found for external_customer_id: {external_customer_id}"
                )
                logfire.error(
                    "User not found for webhook",
                    external_customer_id=external_customer_id,
                )
                raise HTTPException(status_code=404, detail="User not found")

            # Process event based on type
            if event_type == "subscription.active":
                subscription_tier = self._extract_subscription_tier(event_data)
                await self.uow.users.update_subscription(
                    user_id=user_id,
                    subscription_tier=subscription_tier,
                    subscription_status="active",
                    subscription_updated_at=datetime.now(timezone.utc),
                )
                await self.uow.commit()

                logger.info(
                    f"Activated {subscription_tier} subscription for user {user_id}"
                )
                logfire.info(
                    "Subscription activated",
                    user_id=user_id,
                    subscription_tier=subscription_tier,
                )

                return {
                    "status": "success",
                    "message": f"Activated {subscription_tier} subscription for user {user_id}",
                }

            elif event_type == "subscription.canceled":
                # Keep the tier for historical purposes, just change status
                await self.uow.users.update_subscription(
                    user_id=user_id,
                    subscription_tier=user.subscription_tier,
                    subscription_status="canceled",
                    subscription_updated_at=datetime.now(timezone.utc),
                )
                await self.uow.commit()

                logger.info(f"Canceled subscription for user {user_id}")
                logfire.info("Subscription canceled", user_id=user_id)

                return {
                    "status": "success",
                    "message": f"Canceled subscription for user {user_id}",
                }

            return {"status": "unknown", "message": "Unhandled event type"}

    def _extract_subscription_tier(self, event_data: Dict[str, Any]) -> str:
        """
        Extract subscription tier from Polar webhook event data.

        Args:
            event_data: Event data payload from Polar

        Returns:
            Subscription tier name ('starter', 'pro', or 'unknown')
        """
        product = event_data.get("product", {})
        product_name = product.get("name", "").lower()

        # Try to extract from product name first
        if "starter" in product_name:
            return "starter"
        elif "pro" in product_name:
            return "pro"

        # Fallback to product ID matching
        product_id = product.get("id")
        if product_id in [
            settings.POLAR_STARTER_MONTHLY_PRODUCT_ID,
            settings.POLAR_STARTER_YEARLY_PRODUCT_ID,
        ]:
            return "starter"
        elif product_id in [
            settings.POLAR_PRO_MONTHLY_PRODUCT_ID,
            settings.POLAR_PRO_YEARLY_PRODUCT_ID,
        ]:
            return "pro"

        logger.warning(f"Unknown product ID or name: {product_id} / {product_name}")
        logfire.warning(
            "Unknown subscription product",
            product_id=product_id,
            product_name=product_name,
        )
        return "unknown"
