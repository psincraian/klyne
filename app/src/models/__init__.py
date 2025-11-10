from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .user import User as User  # noqa: E402
from .api_key import APIKey as APIKey  # noqa: E402
from .analytics_event import AnalyticsEvent as AnalyticsEvent  # noqa: E402
from .email import Email as Email  # noqa: E402
from .badge_token import BadgeToken as BadgeToken  # noqa: E402
