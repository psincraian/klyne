"""
Klyne Python SDK - Lightweight package analytics

Usage:
    import klyne
    klyne.init(api_key="klyne_your_key", project="your-package")
"""

import os

from .client import (
    _init_internal,
    disable,
    enable,
    flush,
    init,
    is_enabled,
    track,
)
from .version import __version__

__all__ = [
    "init",
    "track",
    "flush",
    "disable",
    "enable",
    "is_enabled",
    "__version__",
]


# Self-analytics initialization for Klyne SDK
def _init_self_analytics():
    """
    Initialize analytics for the Klyne SDK itself.

    This is now opt-in via the KLYNE_SELF_ANALYTICS environment variable
    to prevent unwanted side effects when multiple libraries use Klyne.
    """
    try:
        # Determine the base URL based on environment
        # Use localhost for development, production API otherwise
        is_dev = os.getenv("KLYNE_ENV", "prod").lower() == "dev"
        base_url = "http://localhost:8000" if is_dev else "https://www.klyne.dev"

        # Initialize Klyne to track its own usage (internal client)
        _init_internal(
            api_key="klyne_DWX-CFYhHWhTaZ4Zb8k2tMm5fTX1LPsLW7aR5O4NYF0",
            project="klyne",
            package_version=__version__,
            base_url=base_url,
            enabled=True,
            debug=False,
        )
    except Exception:
        # Silently fail if self-analytics can't be initialized
        # This ensures the SDK still works even if analytics fail
        pass


# Self-analytics is now opt-in to prevent conflicts when multiple libraries use Klyne
# Set KLYNE_SELF_ANALYTICS=1 to enable SDK usage tracking
if os.getenv("KLYNE_SELF_ANALYTICS") == "1":
    _init_self_analytics()
