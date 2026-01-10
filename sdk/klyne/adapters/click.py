"""
Click CLI framework adapter for Klyne analytics.

Provides the `track_click` function to add analytics tracking to Click
CLI applications with a single line of code.

Example:
    import click
    from klyne.adapters import track_click

    @click.group()
    def cli():
        pass

    track_click(cli, api_key="klyne_...", project="my-cli")

    @cli.command()
    def install():
        click.echo("Installing...")
"""

import functools
import logging
import time
from typing import List, Optional

from .base import BaseCLIAdapter, CommandExecution

_logger = logging.getLogger(__name__)


class ClickAdapter(BaseCLIAdapter):
    """Click-specific adapter implementation."""

    pass


def track_click(
    group,
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
    Add Klyne analytics tracking to a Click group or command.

    This function wraps a Click group/command to automatically track:
    - Command name and subcommands
    - Execution duration
    - Success/failure status
    - Exit codes
    - Error information (on failure)
    - Command arguments (if track_args=True)

    Args:
        group: Click group or command to track
        api_key: Klyne API key
        project: Project name for analytics
        package_version: Version of your CLI tool (auto-detected if None)
        base_url: Klyne API URL
        enabled: Enable/disable tracking
        debug: Enable debug logging
        track_args: Whether to track command arguments
        sensitive_args: Additional argument names to always redact

    Returns:
        The same group/command with tracking added

    Example:
        @click.group()
        def cli():
            pass

        track_click(cli, api_key="klyne_...", project="my-cli")

        @cli.command()
        def install():
            click.echo("Installing...")

        if __name__ == "__main__":
            cli()
    """
    try:
        import click
    except ImportError:
        _logger.warning("Click is not installed. Tracking disabled.")
        return group

    adapter = ClickAdapter(
        api_key=api_key,
        project=project,
        package_version=package_version,
        base_url=base_url,
        enabled=enabled,
        debug=debug,
        track_args=track_args,
        sensitive_args=sensitive_args,
    )

    # Store original callback
    original_callback = group.callback

    @functools.wraps(original_callback or (lambda: None))
    def tracked_callback(*args, **kwargs):
        """Wrapped callback that starts timing."""
        ctx = click.get_current_context()

        # Initialize tracking data in context
        ctx.ensure_object(dict)
        ctx.obj["_klyne_start_time"] = time.perf_counter()
        ctx.obj["_klyne_command"] = ctx.info_name or "cli"
        ctx.obj["_klyne_adapter"] = adapter

        # Call original callback if exists
        if original_callback:
            return original_callback(*args, **kwargs)

    # Replace the callback
    group.callback = tracked_callback

    # Check if this is a group (has result_callback method)
    if hasattr(group, "result_callback"):
        # Add result callback to track completion
        @group.result_callback()
        @click.pass_context
        def klyne_result_callback(ctx, result, **kwargs):
            """Track command completion."""
            try:
                start_time = ctx.obj.get("_klyne_start_time", time.perf_counter())
                command_name = ctx.obj.get("_klyne_command", "cli")
                tracked_adapter = ctx.obj.get("_klyne_adapter", adapter)

                execution = CommandExecution(
                    command_name=command_name,
                    subcommand=ctx.invoked_subcommand,
                    args=tracked_adapter._sanitize_args(kwargs),
                    start_time=start_time,
                )
                execution.complete(success=True, exit_code=0)

                tracked_adapter._track_execution(execution)
            except Exception as e:
                _logger.debug(f"Failed to track Click result: {e}")

            return result

    else:
        # For simple commands without subcommands, wrap differently
        original_invoke = group.invoke

        @functools.wraps(original_invoke)
        def tracked_invoke(ctx):
            """Wrapped invoke that tracks execution."""
            start_time = time.perf_counter()
            command_name = ctx.info_name or "cli"

            execution = CommandExecution(
                command_name=command_name,
                start_time=start_time,
            )

            try:
                result = original_invoke(ctx)
                execution.complete(success=True, exit_code=0)
                return result
            except click.ClickException as e:
                execution.complete(
                    success=False,
                    exit_code=e.exit_code,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else 1
                execution.complete(
                    success=(exit_code == 0),
                    exit_code=exit_code,
                )
                raise
            except Exception as e:
                execution.complete(
                    success=False,
                    exit_code=1,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
            finally:
                try:
                    adapter._track_execution(execution)
                except Exception:
                    pass

        group.invoke = tracked_invoke

    return group
