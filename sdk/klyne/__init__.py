"""
Klyne Python SDK - Lightweight package analytics

Usage:
    import klyne
    klyne.init(api_key="klyne_your_key", project="your-package")
"""

from .client import init, track_event, disable, enable, is_enabled, flush
from .version import __version__

__all__ = [
    "init",
    "track_event", 
    "flush",
    "disable",
    "enable",
    "is_enabled",
    "__version__"
]