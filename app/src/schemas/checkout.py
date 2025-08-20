from pydantic import BaseModel
from enum import Enum


class SubscriptionTier(str, Enum):
    STARTER = "starter"
    PRO = "pro"


class SubscriptionInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CheckoutRequest(BaseModel):
    tier: SubscriptionTier
    interval: SubscriptionInterval


class CheckoutResponse(BaseModel):
    checkout_url: str