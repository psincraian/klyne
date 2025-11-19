import secrets
import string
from typing import Optional, List
import logging
from fastapi import HTTPException

from src.models.api_key import APIKey
from src.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for API key management and business logic."""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        # Generate a 32-character API key with prefix
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"klyne_{random_part}"

    async def create_api_key(self, user_id: int, package_name: str, 
                           description: Optional[str] = None) -> APIKey:
        """Create a new API key for a user and package."""
        # Check if user exists
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check subscription requirements
        if not user.subscription_tier or user.subscription_status != "active":
            raise HTTPException(
                status_code=403, 
                detail="An active subscription is required to create API keys. Please subscribe to get started."
            )

        # Check if user can create more API keys based on subscription limits
        from src.services.subscription_service import SubscriptionService
        subscription_service = SubscriptionService(self.uow)
        can_create = await subscription_service.can_create_api_key(user_id)
        if not can_create:
            limits = await subscription_service.get_subscription_limits(user_id)
            max_keys = limits["limits"]["max_api_keys"]
            raise HTTPException(
                status_code=403, 
                detail=f"You've reached the limit of {max_keys} API key{'s' if max_keys != 1 else ''} for your {user.subscription_tier.title()} plan. Please upgrade to Pro to create more API keys."
            )

        # Check if user already has an API key for this package
        existing_key = await self.uow.api_keys.get_by_user_and_package(user_id, package_name)
        if existing_key:
            raise HTTPException(
                status_code=400, 
                detail=f"API key already exists for package '{package_name}'"
            )

        # Generate unique API key
        max_attempts = 10
        for attempt in range(max_attempts):
            api_key = self._generate_api_key()
            
            # Check if key already exists
            if not await self.uow.api_keys.key_exists(api_key):
                break
                
            if attempt == max_attempts - 1:
                raise HTTPException(status_code=500, detail="Failed to generate unique API key")

        # Create the API key
        new_api_key = await self.uow.api_keys.create_api_key(
            user_id=user_id,
            package_name=package_name,
            key=api_key,
            description=description
        )

        await self.uow.commit()
        logger.info(f"Created API key for user {user.email}, package {package_name}")
        return new_api_key

    async def get_user_api_keys(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return await self.uow.api_keys.get_by_user_id(user_id)

    async def get_user_active_api_keys(self, user_id: int) -> List[APIKey]:
        """Get all active API keys for a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return await self.uow.api_keys.get_active_keys_by_user(user_id)

    async def get_api_key_by_key(self, key: str) -> Optional[APIKey]:
        """Get API key by key value."""
        return await self.uow.api_keys.get_by_key(key)

    async def validate_api_key(self, key: str) -> Optional[APIKey]:
        """Validate an API key and return it if valid and active."""
        api_key = await self.uow.api_keys.get_by_key(key)
        
        if not api_key:
            return None
            
        if not api_key.is_active:
            return None
            
        # Check if the associated user is active
        user = await self.uow.users.get_by_id(api_key.user_id)
        if not user or not user.is_active:
            return None
            
        return api_key

    async def deactivate_api_key(self, user_id: int, api_key_id: int) -> APIKey:
        """Deactivate an API key (user can only deactivate their own keys)."""
        # Get the API key
        api_key = await self.uow.api_keys.get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Check if the API key belongs to the user
        if api_key.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this API key")

        # Deactivate the key
        deactivated_key = await self.uow.api_keys.deactivate_key(api_key_id)
        await self.uow.commit()
        
        logger.info(f"Deactivated API key {api_key.key} for user {user_id}")
        return deactivated_key

    async def activate_api_key(self, user_id: int, api_key_id: int) -> APIKey:
        """Activate an API key (user can only activate their own keys)."""
        # Get the API key
        api_key = await self.uow.api_keys.get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Check if the API key belongs to the user
        if api_key.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this API key")

        # Activate the key
        activated_key = await self.uow.api_keys.activate_key(api_key_id)
        await self.uow.commit()
        
        logger.info(f"Activated API key {api_key.key} for user {user_id}")
        return activated_key

    async def delete_api_key(self, user_id: int, api_key_id: int) -> bool:
        """Delete an API key (user can only delete their own keys)."""
        # Get the API key
        api_key = await self.uow.api_keys.get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Check if the API key belongs to the user
        if api_key.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this API key")

        # Delete the key
        deleted = await self.uow.api_keys.delete(api_key_id)
        await self.uow.commit()
        
        if deleted:
            logger.info(f"Deleted API key {api_key.key} for user {user_id}")
        
        return deleted

    async def get_api_key_stats(self, user_id: int) -> dict:
        """Get API key statistics for a user."""
        total_keys = await self.uow.api_keys.count_keys_by_user(user_id)
        active_keys = await self.uow.api_keys.count_active_keys_by_user(user_id)
        packages = await self.uow.api_keys.get_packages_for_user(user_id)
        
        return {
            "user_id": user_id,
            "total_keys": total_keys,
            "active_keys": active_keys,
            "inactive_keys": total_keys - active_keys,
            "total_packages": len(packages),
            "packages": packages
        }

    async def get_package_api_keys(self, package_name: str) -> List[APIKey]:
        """Get all API keys for a specific package (admin only)."""
        return await self.uow.api_keys.get_by_package_name(package_name)

    async def get_active_package_api_keys(self, package_name: str) -> List[APIKey]:
        """Get all active API keys for a specific package (admin only)."""
        return await self.uow.api_keys.get_active_keys_by_package(package_name)

    async def regenerate_api_key(self, user_id: int, api_key_id: int) -> APIKey:
        """Regenerate an API key with a new key value."""
        # Get the existing API key
        api_key = await self.uow.api_keys.get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Check if the API key belongs to the user
        if api_key.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this API key")

        # Generate new API key
        max_attempts = 10
        for attempt in range(max_attempts):
            new_key = self._generate_api_key()
            
            # Check if key already exists
            if not await self.uow.api_keys.key_exists(new_key):
                break
                
            if attempt == max_attempts - 1:
                raise HTTPException(status_code=500, detail="Failed to generate unique API key")

        # Update the API key
        updated_key = await self.uow.api_keys.update(api_key_id, {"key": new_key})
        await self.uow.commit()
        
        logger.info(f"Regenerated API key for user {user_id}, package {api_key.package_name}")
        return updated_key

    async def user_can_create_api_key(self, user_id: int) -> bool:
        """Check if user can create more API keys based on their subscription."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return False

        # Check if user has active subscription and is within limits
        if not user.subscription_tier or user.subscription_status != "active":
            return False

        # Check against package limits using subscription service
        from src.services.subscription_service import SubscriptionService
        subscription_service = SubscriptionService(self.uow)
        return await subscription_service.can_create_api_key(user_id)

    async def get_api_key_by_user_and_package(self, user_id: int, package_name: str) -> Optional[APIKey]:
        """Get API key for a specific user and package combination."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return await self.uow.api_keys.get_by_user_and_package(user_id, package_name)

    async def ensure_api_key_exists(self, user_id: int, package_name: str,
                                  description: Optional[str] = None) -> APIKey:
        """Ensure an API key exists for user and package, create if it doesn't exist."""
        existing_key = await self.uow.api_keys.get_by_user_and_package(user_id, package_name)

        if existing_key:
            return existing_key

        return await self.create_api_key(user_id, package_name, description)

    async def update_badge_visibility(self, user_id: int, api_key_id: int, is_public: bool) -> dict:
        """Update or create badge visibility for an API key."""
        # Get the API key
        api_key = await self.uow.api_keys.get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Check if the API key belongs to the user
        if api_key.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this API key")

        # Get or create badge
        badge = await self.uow.badges.get_by_api_key_id(api_key_id)

        if badge:
            # Update existing badge
            badge = await self.uow.badges.update_visibility(badge.id, is_public)
        else:
            # Create new badge when making public
            if is_public:
                from src.models.badge import Badge
                badge_uuid = Badge.generate_uuid()
                badge = await self.uow.badges.create_badge(api_key_id, badge_uuid, is_public)
            else:
                # If setting to private and no badge exists, nothing to do
                await self.uow.commit()
                logger.info(f"No badge to update for API key {api_key.key}, user {user_id}")
                return {"success": True, "badge_public": False}

        await self.uow.commit()
        logger.info(f"Updated badge visibility to {is_public} for API key {api_key.key}, user {user_id}")

        return {
            "success": True,
            "badge_public": badge.is_public if badge else False,
            "badge_uuid": str(badge.badge_uuid) if badge else None
        }

    async def get_badge_data_by_uuid(self, badge_uuid: str) -> Optional[dict]:
        """Get badge data for a public badge using UUID."""
        import uuid as uuid_lib

        # Parse UUID
        try:
            uuid_obj = uuid_lib.UUID(badge_uuid)
        except (ValueError, AttributeError):
            return None

        # Get the badge by UUID
        badge = await self.uow.badges.get_by_uuid(uuid_obj)
        if not badge:
            return None

        # Check if badge is public
        if not badge.is_public:
            return None

        # Get the API key to get package name
        api_key = await self.uow.api_keys.get_by_id(badge.api_key_id)
        if not api_key:
            return None

        # Get unique users count (all time)
        unique_users = await self.uow.analytics_events.get_unique_users_count([api_key.key])

        return {
            "package_name": api_key.package_name,
            "unique_users": unique_users,
            "is_public": True
        }