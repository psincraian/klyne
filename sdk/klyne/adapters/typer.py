"""
Typer CLI framework adapter for Klyne analytics.

Provides the `track_typer` function to add analytics tracking to Typer
CLI applications with a single line of code.

Example:
    import typer
    from klyne.adapters import track_typer

    app = typer.Typer()
    track_typer(app, api_key="klyne_...", project="my-cli")

    @app.command()
    def install(name: str):
        print(f"Installing {name}...")
"""

import atexit
import logging
import time
from typing import List, Optional

from .base import BaseCLIAdapter, CommandExecution

_logger = logging.getLogger(__name__)


class TyperAdapter(BaseCLIAdapter):
    """Typer-specific adapter implementation."""

    pass


# Thread-local storage for tracking state
_tracking_state = {}


def track_typer(
    app,
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
    Add Klyne analytics tracking to a Typer app.

    This function wraps a Typer app to automatically track:
    - Command name and subcommands
    - Execution duration
    - Success/failure status
    - Exit codes
    - Error information (on failure)
    - Command arguments (if track_args=True)

    Args:
        app: Typer app to track
        api_key: Klyne API key
        project: Project name for analytics
        package_version: Version of your CLI tool (auto-detected if None)
        base_url: Klyne API URL
        enabled: Enable/disable tracking
        debug: Enable debug logging
        track_args: Whether to track command arguments
        sensitive_args: Additional argument names to always redact

    Returns:
        The same app with tracking added

    Example:
        import typer
        from klyne.adapters import track_typer

        app = typer.Typer()
        track_typer(app, api_key="klyne_...", project="my-cli")

        @app.command()
        def install(name: str):
            print(f"Installing {name}...")

        if __name__ == "__main__":
            app()
    """
    try:
        import typer
    except ImportError:
        _logger.warning("Typer is not installed. Tracking disabled.")
        return app

    adapter = TyperAdapter(
        api_key=api_key,
        project=project,
        package_version=package_version,
        base_url=base_url,
        enabled=enabled,
        debug=debug,
        track_args=track_args,
        sensitive_args=sensitive_args,
    )

    # Create a unique key for this app instance
    app_id = id(app)

    def track_on_exit():
        """Track execution when the CLI exits."""
        state = _tracking_state.get(app_id)
        if state and not state.get("tracked"):
            try:
                execution = state.get("execution")
                if execution:
                    execution.complete(
                        success=state.get("success", True),
                        exit_code=state.get("exit_code", 0),
                        error_type=state.get("error_type"),
                        error_message=state.get("error_message"),
                    )
                    adapter._track_execution(execution)
                    state["tracked"] = True
            except Exception as e:
                _logger.debug(f"Failed to track Typer execution on exit: {e}")

    # Register cleanup
    atexit.register(track_on_exit)

    # Check if callback already exists
    existing_callback = None
    if hasattr(app, "registered_callback") and app.registered_callback:
        existing_callback = app.registered_callback

    @app.callback(invoke_without_command=True)
    def klyne_callback(ctx: typer.Context):
        """Initialize tracking when CLI starts."""
        # Initialize tracking state
        execution = CommandExecution(
            command_name=ctx.info_name or "cli",
            start_time=time.perf_counter(),
        )

        _tracking_state[app_id] = {
            "execution": execution,
            "tracked": False,
            "success": True,
            "exit_code": 0,
        }

        # Store in context for subcommands
        ctx.ensure_object(dict)
        ctx.obj["_klyne_execution"] = execution
        ctx.obj["_klyne_adapter"] = adapter
        ctx.obj["_klyne_app_id"] = app_id

        # Call existing callback if any
        if existing_callback:
            return existing_callback(ctx)

    # Wrap each registered command to track its execution
    original_command = app.command

    def tracked_command(*args, **kwargs):
        """Decorator that wraps command registration with tracking."""
        decorator = original_command(*args, **kwargs)

        def wrapper(func):
            import functools

            @functools.wraps(func)
            def tracked_func(*f_args, **f_kwargs):
                # Get context from typer
                try:
                    ctx = typer.get_current_context()
                    execution = ctx.obj.get("_klyne_execution") if ctx.obj else None

                    if execution:
                        # Update with subcommand info
                        execution.subcommand = ctx.info_name
                        execution.args = adapter._sanitize_args(f_kwargs)
                except Exception:
                    execution = None

                try:
                    result = func(*f_args, **f_kwargs)

                    # Mark as successful
                    if app_id in _tracking_state:
                        _tracking_state[app_id]["success"] = True
                        _tracking_state[app_id]["exit_code"] = 0

                    return result

                except typer.Exit as e:
                    if app_id in _tracking_state:
                        _tracking_state[app_id]["success"] = (e.exit_code == 0)
                        _tracking_state[app_id]["exit_code"] = e.exit_code
                    raise

                except typer.Abort:
                    if app_id in _tracking_state:
                        _tracking_state[app_id]["success"] = False
                        _tracking_state[app_id]["exit_code"] = 1
                        _tracking_state[app_id]["error_type"] = "Abort"
                    raise

                except Exception as e:
                    if app_id in _tracking_state:
                        _tracking_state[app_id]["success"] = False
                        _tracking_state[app_id]["exit_code"] = 1
                        _tracking_state[app_id]["error_type"] = type(e).__name__
                        _tracking_state[app_id]["error_message"] = str(e)
                    raise

            return decorator(tracked_func)

        return wrapper

    app.command = tracked_command

    return app
