"""
Main Klyne SDK client implementation.
"""

import atexit
import logging
from typing import Any, Dict, Optional

from .collector import create_analytics_event, create_session_id
from .transport import HTTPTransport

# Global SDK state
_client = None
_internal_client = None  # Separate client for internal analytics
_logger = logging.getLogger(__name__)


class KlyneClient:
    """Main Klyne analytics client."""

    def __init__(
        self,
        api_key: str,
        project: str,
        package_version: str = "unknown",
        base_url: str = "https://www.klyne.dev",
        enabled: bool = True,
        debug: bool = False,
    ):
        """
        Initialize Klyne client.

        Args:
            api_key: Klyne API key
            project: Package/project name
            package_version: Version of your package
            base_url: Klyne API base URL
            enabled: Whether analytics are enabled
            debug: Enable debug logging
        """
        self.api_key = api_key
        self.project = project
        self.package_version = package_version
        self.enabled = enabled
        self.session_id = create_session_id()

        # Set up logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)

        # Initialize transport
        self.transport = None
        if enabled:
            try:
                self.transport = HTTPTransport(api_key=api_key, base_url=base_url)
            except Exception as e:
                _logger.warning(f"Failed to initialize Klyne transport: {e}")
                self.enabled = False

        # Register cleanup on exit
        atexit.register(self._cleanup)

        # Send initial event
        if self.enabled:
            self._send_init_event()

    def _send_init_event(self):
        """Send initial package initialization event."""
        try:
            event = create_analytics_event(
                api_key=self.api_key,
                package_name=self.project,
                package_version=self.package_version,
                session_id=self.session_id,
                entry_point="init",
            )

            if self.transport:
                self.transport.send_event(event)

        except Exception as e:
            _logger.warning(f"Failed to send Klyne init event: {e}")

    def track_event(
        self,
        entry_point: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Track a custom analytics event.

        Args:
            entry_point: Function or entry point name
            extra_data: Additional custom data
            session_id: Optional custom session ID
        """
        if not self.enabled or not self.transport:
            return

        try:
            event = create_analytics_event(
                api_key=self.api_key,
                package_name=self.project,
                package_version=self.package_version,
                session_id=session_id or self.session_id,
                entry_point=entry_point,
                extra_data=extra_data,
            )

            self.transport.send_event(event)

        except Exception as e:
            _logger.warning(f"Failed to send Klyne event: {e}")

    def flush(self, timeout: float = 10.0):
        """
        Flush all pending events.

        Args:
            timeout: Maximum time to wait for flush
        """
        if self.transport:
            self.transport.flush(timeout)

    def disable(self):
        """Disable analytics tracking."""
        self.enabled = False
        if self.transport:
            self.transport.disable()

    def enable(self):
        """Enable analytics tracking."""
        self.enabled = True
        if self.transport:
            self.transport.enable()
        elif not self.transport:
            # Re-initialize transport if it was never created
            try:
                self.transport = HTTPTransport(api_key=self.api_key)
            except Exception as e:
                _logger.warning(f"Failed to re-initialize Klyne transport: {e}")

    def is_enabled(self) -> bool:
        """Check if analytics are enabled."""
        return self.enabled and self.transport and self.transport.is_enabled()

    def _cleanup(self):
        """Cleanup on exit."""
        if self.transport:
            self.transport.shutdown()


# Public API functions
def init(
    api_key: str,
    project: str,
    package_version: str = "unknown",
    base_url: str = "https://www.klyne.dev",
    enabled: bool = True,
    debug: bool = False,
    _internal: bool = False,
) -> None:
    """
    Initialize Klyne analytics for your package.

    Args:
        api_key: Your Klyne API key (get from https://www.klyne.dev)
        project: Your package name (must match API key)
        package_version: Version of your package
        base_url: Klyne API base URL (default: https://www.klyne.dev)
        enabled: Whether to enable analytics (default: True)
        debug: Enable debug logging (default: False)
        _internal: Internal flag for SDK self-analytics (private)

    Example:
        import klyne
        klyne.init(
            api_key="klyne_your_api_key_here",
            project="your-package-name",
            package_version="1.0.0"
        )
    """
    global _client, _internal_client

    # Handle internal analytics separately
    if _internal:
        if _internal_client is not None:
            return  # Internal client already initialized
        try:
            _internal_client = KlyneClient(
                api_key=api_key,
                project=project,
                package_version=package_version,
                base_url=base_url,
                enabled=enabled,
                debug=debug,
            )
        except Exception as e:
            _logger.debug(f"Failed to initialize internal Klyne: {e}")
        return

    # Handle customer analytics
    if _client is not None:
        _logger.warning("Klyne already initialized for this project, skipping")
        return

    try:
        _client = KlyneClient(
            api_key=api_key,
            project=project,
            package_version=package_version,
            base_url=base_url,
            enabled=enabled,
            debug=debug,
        )
    except Exception as e:
        _logger.warning(f"Failed to initialize Klyne: {e}")


def track_event(
    entry_point: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Track a custom analytics event.

    Args:
        entry_point: Function or entry point name
        extra_data: Additional custom data
        session_id: Optional custom session ID

    Example:
        import klyne
        klyne.track_event(
            entry_point="my_function",
            extra_data={"feature": "advanced_mode"}
        )
    """
    if _client:
        _client.track_event(entry_point, extra_data, session_id)


def flush(timeout: float = 10.0) -> None:
    """
    Flush all pending analytics events.

    Args:
        timeout: Maximum time to wait for flush completion
    """
    if _client:
        _client.flush(timeout)


def disable() -> None:
    """Disable Klyne analytics tracking."""
    if _client:
        _client.disable()


def enable() -> None:
    """Enable Klyne analytics tracking."""
    if _client:
        _client.enable()


def is_enabled() -> bool:
    """
    Check if Klyne analytics are enabled.

    Returns:
        True if analytics are enabled and working
    """
    return _client.is_enabled() if _client else False


def _init_internal(
    api_key: str,
    project: str,
    package_version: str = "unknown",
    base_url: str = "https://www.klyne.dev",
    enabled: bool = True,
    debug: bool = False,
) -> None:
    """
    Initialize internal Klyne analytics (for SDK self-tracking).
    This is separate from customer analytics to avoid conflicts.
    """
    init(
        api_key=api_key,
        project=project,
        package_version=package_version,
        base_url=base_url,
        enabled=enabled,
        debug=debug,
        _internal=True,
    )


# Helper for package version detection
def _detect_package_version(package_name: str) -> str:
    """Try to auto-detect package version."""
    try:
        # Try importlib.metadata first (Python 3.8+)
        try:
            from importlib.metadata import version

            return version(package_name)
        except ImportError:
            # Fallback to pkg_resources
            import pkg_resources

            return pkg_resources.get_distribution(package_name).version
    except Exception:
        return "unknown"
