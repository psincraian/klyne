"""
Main Klyne SDK client implementation.
"""

import atexit
import logging
from typing import Any, Dict, Optional

from .collector import create_analytics_event, create_session_id
from .installation import get_or_create_installation_id, get_user_identifier
from .transport import HTTPTransport

# Global SDK state
_clients: Dict[str, "KlyneClient"] = {}  # Registry of all clients by project name
_default_client: Optional["KlyneClient"] = None  # Most recent client (for backward compat)
_internal_client: Optional["KlyneClient"] = None  # Separate client for internal analytics
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

        # Initialize unique user tracking
        self.installation_id, self.fingerprint_hash = get_or_create_installation_id(project)
        self.user_identifier = get_user_identifier(self.installation_id, self.fingerprint_hash)

        # Set up logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            if self.installation_id:
                _logger.debug(f"Klyne initialized with installation ID: {self.installation_id}")
            else:
                _logger.debug("Klyne initialized with fingerprint tracking only")

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
                installation_id=self.installation_id,
                fingerprint_hash=self.fingerprint_hash,
                user_identifier=self.user_identifier,
            )

            if self.transport:
                self.transport.send_event(event)

        except Exception as e:
            _logger.warning(f"Failed to send Klyne init event: {e}")

    def track(
        self,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Track a custom event with properties.

        This method merges custom properties at the root level of the analytics
        event alongside system-collected metrics.

        Args:
            event_name: Name of the event (e.g., 'user_login', 'feature_used')
            properties: Custom properties to track with the event
            session_id: Optional custom session ID

        Example:
            client.track('user_login', {
                'user_id': '12345',
                'login_method': 'google'
            })
        """
        if not self.enabled or not self.transport:
            return

        try:
            event = create_analytics_event(
                api_key=self.api_key,
                package_name=self.project,
                package_version=self.package_version,
                session_id=session_id or self.session_id,
                entry_point=event_name,
                properties=properties,
                installation_id=self.installation_id,
                fingerprint_hash=self.fingerprint_hash,
                user_identifier=self.user_identifier,
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
) -> Optional[KlyneClient]:
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

    Returns:
        KlyneClient instance for this project (or None on failure)

    Example:
        import klyne

        # Option 1: Module-level API (backward compatible)
        klyne.init(
            api_key="klyne_your_api_key_here",
            project="your-package-name",
            package_version="1.0.0"
        )
        klyne.track("event_name")

        # Option 2: Instance-based API (recommended for libraries)
        client = klyne.init(
            api_key="klyne_your_api_key_here",
            project="your-package-name",
            package_version="1.0.0"
        )
        client.track("event_name")
    """
    global _clients, _default_client, _internal_client

    # Handle internal analytics separately
    if _internal:
        if _internal_client is not None:
            return _internal_client  # Internal client already initialized
        try:
            _internal_client = KlyneClient(
                api_key=api_key,
                project=project,
                package_version=package_version,
                base_url=base_url,
                enabled=enabled,
                debug=debug,
            )
            return _internal_client
        except Exception as e:
            _logger.debug(f"Failed to initialize internal Klyne: {e}")
            return None

    # Check if client already exists for this project
    if project in _clients:
        _logger.info(f"Klyne already initialized for project '{project}', returning existing client")
        return _clients[project]

    # Create new client for this project
    try:
        client = KlyneClient(
            api_key=api_key,
            project=project,
            package_version=package_version,
            base_url=base_url,
            enabled=enabled,
            debug=debug,
        )

        # Register the client
        _clients[project] = client
        _default_client = client  # Set as default for backward compatibility

        return client
    except Exception as e:
        _logger.warning(f"Failed to initialize Klyne: {e}")
        return None


def track(
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Track a custom event with properties.

    This method merges custom properties at the root level of the analytics
    event alongside system-collected metrics.

    Args:
        event_name: Name of the event (e.g., 'user_login', 'feature_used')
        properties: Custom properties to track with the event
        session_id: Optional custom session ID

    Example:
        import klyne
        klyne.init(api_key="klyne_...", project="my-package")

        # Track custom events
        klyne.track('user_login', {
            'user_id': '12345',
            'login_method': 'google'
        })

        klyne.track('feature_used', {
            'feature_name': 'export',
            'file_format': 'csv'
        })
    """
    if _default_client:
        _default_client.track(event_name, properties, session_id)


def flush(timeout: float = 10.0) -> None:
    """
    Flush all pending analytics events.

    Args:
        timeout: Maximum time to wait for flush completion
    """
    if _default_client:
        _default_client.flush(timeout)


def disable() -> None:
    """Disable Klyne analytics tracking."""
    if _default_client:
        _default_client.disable()


def enable() -> None:
    """Enable Klyne analytics tracking."""
    if _default_client:
        _default_client.enable()


def is_enabled() -> bool:
    """
    Check if Klyne analytics are enabled.

    Returns:
        True if analytics are enabled and working
    """
    return _default_client.is_enabled() if _default_client else False


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
