"""
Base classes for CLI framework adapters.

This module provides shared functionality for tracking CLI command executions
across different frameworks (Click, Typer, argparse).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

_logger = logging.getLogger(__name__)

# Default sensitive argument names to redact
DEFAULT_SENSITIVE_ARGS: Set[str] = {
    "password",
    "passwd",
    "token",
    "secret",
    "key",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "private",
}


@dataclass
class CommandExecution:
    """Captures data about a CLI command execution."""

    command_name: str
    subcommand: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    exit_code: int = 0
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def complete(
        self,
        success: bool = True,
        exit_code: int = 0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark the execution as complete and calculate duration."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.exit_code = exit_code
        self.error_type = error_type
        self.error_message = error_message


def _detect_package_version(project: str) -> str:
    """
    Try to auto-detect package version from installed metadata.

    Args:
        project: Package name to look up

    Returns:
        Version string or "unknown" if not found
    """
    try:
        from importlib.metadata import version

        return version(project)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        import pkg_resources

        return pkg_resources.get_distribution(project).version
    except Exception:
        pass

    return "unknown"


class BaseCLIAdapter:
    """
    Base class for CLI framework adapters.

    Provides common functionality for tracking CLI command executions
    including lazy client initialization, argument sanitization, and
    event tracking.
    """

    def __init__(
        self,
        api_key: str,
        project: str,
        *,
        package_version: Optional[str] = None,
        base_url: str = "https://www.klyne.dev",
        enabled: bool = True,
        debug: bool = False,
        track_args: bool = False,
        sensitive_args: Optional[List[str]] = None,
    ):
        """
        Initialize CLI adapter.

        Args:
            api_key: Klyne API key
            project: Project/package name for analytics
            package_version: Version of your CLI tool (auto-detected if None)
            base_url: Klyne API URL
            enabled: Enable/disable tracking
            debug: Enable debug logging
            track_args: Whether to include command arguments in analytics
            sensitive_args: Additional argument names to always redact
        """
        self._client = None
        self._api_key = api_key
        self._project = project
        self._base_url = base_url
        self._enabled = enabled
        self._debug = debug
        self._track_args = track_args

        # Auto-detect version if not provided
        if package_version is None:
            self._package_version = _detect_package_version(project)
        else:
            self._package_version = package_version

        # Build set of sensitive argument names
        self._sensitive_args = DEFAULT_SENSITIVE_ARGS.copy()
        if sensitive_args:
            self._sensitive_args.update(arg.lower() for arg in sensitive_args)

        if debug:
            logging.basicConfig(level=logging.DEBUG)
            _logger.debug(
                f"CLI adapter initialized for {project} v{self._package_version}"
            )

    def _get_client(self):
        """
        Lazy initialization of Klyne client.

        Returns:
            KlyneClient instance or None if initialization fails
        """
        if self._client is None:
            try:
                import klyne

                self._client = klyne.init(
                    api_key=self._api_key,
                    project=self._project,
                    package_version=self._package_version,
                    base_url=self._base_url,
                    enabled=self._enabled,
                    debug=self._debug,
                )
            except Exception as e:
                _logger.debug(f"Failed to initialize Klyne client: {e}")
                return None
        return self._client

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or redact sensitive arguments from tracking data.

        Args:
            args: Dictionary of command arguments

        Returns:
            Sanitized dictionary safe for analytics
        """
        if not self._track_args:
            return {}

        if not args:
            return {}

        sanitized = {}
        for key, value in args.items():
            key_lower = key.lower()

            # Redact sensitive args
            if any(s in key_lower for s in self._sensitive_args):
                sanitized[key] = "[REDACTED]"
            # Only include simple serializable types
            elif isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = value
            elif isinstance(value, (list, tuple)):
                # Include list/tuple if all items are simple types
                if all(isinstance(v, (str, int, float, bool, type(None))) for v in value):
                    sanitized[key] = list(value)
                else:
                    sanitized[key] = f"<{type(value).__name__}[{len(value)}]>"
            else:
                sanitized[key] = f"<{type(value).__name__}>"

        return sanitized

    def _track_execution(self, execution: CommandExecution) -> None:
        """
        Track a command execution event.

        Args:
            execution: CommandExecution instance with execution data
        """
        try:
            client = self._get_client()
            if not client:
                return

            # Build event name: "cli:{command}" or "cli:{command}:{subcommand}"
            event_name = f"cli:{execution.command_name}"
            if execution.subcommand:
                event_name = f"{event_name}:{execution.subcommand}"

            # Build properties
            properties: Dict[str, Any] = {
                "cli_command": execution.command_name,
                "cli_duration_ms": round(execution.duration_ms, 2) if execution.duration_ms else None,
                "cli_success": execution.success,
                "cli_exit_code": execution.exit_code,
            }

            if execution.subcommand:
                properties["cli_subcommand"] = execution.subcommand

            if execution.args:
                properties["cli_args"] = execution.args

            if execution.error_type:
                properties["cli_error_type"] = execution.error_type
                # Truncate error message to 500 chars
                if execution.error_message:
                    properties["cli_error_message"] = execution.error_message[:500]

            client.track(event_name, properties)

            if self._debug:
                _logger.debug(f"Tracked CLI event: {event_name} -> {properties}")

        except Exception as e:
            # Graceful failure - never break the CLI
            _logger.debug(f"Failed to track CLI execution: {e}")
