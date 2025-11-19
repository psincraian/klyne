"""
Click adapter for automatic CLI command tracking.

This module provides seamless integration with Click CLI applications,
automatically tracking all command invocations without requiring
manual instrumentation.

Usage:
    import click
    import klyne
    from klyne.click_adapter import ClickModule

    # Initialize Klyne
    klyne.init(api_key="klyne_your_key", project="my-cli")

    # Create your Click CLI
    @click.group()
    def cli():
        '''My awesome CLI'''
        pass

    @cli.command()
    @click.option('--name', default='World')
    def hello(name):
        '''Say hello'''
        click.echo(f'Hello {name}!')

    # Wrap with ClickModule for automatic tracking
    if __name__ == '__main__':
        ClickModule(cli)()
"""

import functools
import logging
import time
from typing import Any, Callable, Optional

try:
    import click
except ImportError:
    click = None  # Click is an optional dependency

from . import client as klyne_client

_logger = logging.getLogger(__name__)


class ClickModule:
    """
    Wrapper for Click CLI applications that enables automatic command tracking.

    This class wraps a Click Group or Command and automatically tracks all
    command invocations with detailed metadata including arguments, options,
    execution time, and success/failure status.

    Args:
        cli: Click Group or Command instance to wrap
        track_arguments: Whether to track command arguments (default: True)
        track_options: Whether to track command options (default: True)
        client: Optional KlyneClient instance (uses default client if not provided)

    Example:
        @click.group()
        def cli():
            pass

        @cli.command()
        def deploy():
            pass

        if __name__ == '__main__':
            ClickModule(cli)()
    """

    def __init__(
        self,
        cli: Any,
        track_arguments: bool = True,
        track_options: bool = True,
        client: Optional[Any] = None,
    ):
        """Initialize the Click adapter."""
        if click is None:
            raise ImportError(
                "Click is not installed. Install it with: pip install click"
            )

        self.cli = cli
        self.track_arguments = track_arguments
        self.track_options = track_options
        self.client = client or klyne_client._default_client

        if self.client is None:
            _logger.warning(
                "Klyne not initialized. Call klyne.init() before creating ClickModule. "
                "Commands will not be tracked."
            )

        # Instrument the CLI
        self._instrument_cli(cli)

    def _instrument_cli(self, cli: Any) -> None:
        """
        Recursively instrument all commands in the CLI.

        Args:
            cli: Click Group or Command to instrument
        """
        if isinstance(cli, click.Group):
            # Instrument group commands
            self._instrument_group(cli)
        elif isinstance(cli, click.Command):
            # Instrument single command
            self._instrument_command(cli)

    def _instrument_group(self, group: click.Group) -> None:
        """
        Instrument a Click Group and all its commands.

        Args:
            group: Click Group to instrument
        """
        # Wrap the group's invoke method
        original_invoke = group.invoke

        @functools.wraps(original_invoke)
        def wrapped_invoke(ctx: click.Context) -> Any:
            """Wrapped invoke that tracks group invocation."""
            return original_invoke(ctx)

        group.invoke = wrapped_invoke

        # Instrument all commands in the group
        for name, command in group.commands.items():
            if isinstance(command, click.Group):
                self._instrument_group(command)
            else:
                self._instrument_command(command, parent_name=group.name)

    def _instrument_command(
        self,
        command: click.Command,
        parent_name: Optional[str] = None
    ) -> None:
        """
        Instrument a Click Command to track its invocations.

        Args:
            command: Click Command to instrument
            parent_name: Name of parent group (if any)
        """
        original_invoke = command.invoke

        @functools.wraps(original_invoke)
        def wrapped_invoke(ctx: click.Context) -> Any:
            """Wrapped invoke that tracks command execution."""
            # Build command name with parent hierarchy
            command_parts = []

            # Walk up the context chain to build full command path
            context = ctx
            while context is not None:
                if context.info_name:
                    command_parts.insert(0, context.info_name)
                context = context.parent

            command_name = " ".join(command_parts) if command_parts else command.name

            # Start timing
            start_time = time.time()
            error_info = None
            success = True

            try:
                # Execute the original command
                result = original_invoke(ctx)
                return result

            except Exception as e:
                # Track error information
                success = False
                error_info = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                raise

            finally:
                # Calculate execution time
                execution_time_ms = (time.time() - start_time) * 1000

                # Track the command invocation
                self._track_command(
                    command_name=command_name,
                    ctx=ctx,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_info=error_info,
                )

        command.invoke = wrapped_invoke

    def _track_command(
        self,
        command_name: str,
        ctx: click.Context,
        success: bool,
        execution_time_ms: float,
        error_info: Optional[dict] = None,
    ) -> None:
        """
        Track a command invocation event.

        Args:
            command_name: Full command name (including parent groups)
            ctx: Click context
            success: Whether command succeeded
            execution_time_ms: Command execution time in milliseconds
            error_info: Error information if command failed
        """
        if self.client is None or not self.client.is_enabled():
            return

        try:
            # Build properties dictionary
            properties = {
                "command_name": command_name,
                "success": success,
                "execution_time_ms": round(execution_time_ms, 2),
            }

            # Add arguments if tracking enabled
            if self.track_arguments and ctx.params:
                # Separate arguments and options
                arguments = {}
                options = {}

                for param_name, param_value in ctx.params.items():
                    # Find the parameter definition
                    param_obj = None
                    for param in ctx.command.params:
                        if param.name == param_name:
                            param_obj = param
                            break

                    # Classify as argument or option
                    if param_obj and isinstance(param_obj, click.Argument):
                        arguments[param_name] = param_value
                    else:
                        options[param_name] = param_value

                if arguments:
                    properties["arguments"] = arguments

                if options and self.track_options:
                    properties["options"] = options

            # Add error information if present
            if error_info:
                properties.update(error_info)

            # Track the event
            event_name = f"cli.{command_name.replace(' ', '.')}"
            self.client.track(event_name, properties)

        except Exception as e:
            # Silently fail - don't break the CLI if tracking fails
            _logger.debug(f"Failed to track Click command: {e}")

    def __call__(self, *args, **kwargs) -> Any:
        """
        Make the wrapper callable so it can be used as: ClickModule(cli)()

        This allows seamless replacement of cli() with ClickModule(cli)()
        """
        return self.cli(*args, **kwargs)


def track_click_command(
    func: Optional[Callable] = None,
    *,
    track_arguments: bool = True,
    track_options: bool = True,
    client: Optional[Any] = None,
) -> Callable:
    """
    Decorator to track individual Click commands.

    This provides an alternative to ClickModule for cases where you want
    to selectively track specific commands rather than the entire CLI.

    Args:
        func: Function to decorate (provided automatically when used as decorator)
        track_arguments: Whether to track command arguments
        track_options: Whether to track command options
        client: Optional KlyneClient instance

    Example:
        @click.command()
        @click.option('--count', default=1)
        @track_click_command
        def hello(count):
            for _ in range(count):
                click.echo('Hello!')
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            # Get the Click context
            ctx = click.get_current_context()

            # Determine which client to use
            tracking_client = client or klyne_client._default_client

            if tracking_client is None or not tracking_client.is_enabled():
                return f(*args, **kwargs)

            # Build command name
            command_parts = []
            context = ctx
            while context is not None:
                if context.info_name:
                    command_parts.insert(0, context.info_name)
                context = context.parent

            command_name = " ".join(command_parts) if command_parts else ctx.info_name

            # Track execution
            start_time = time.time()
            error_info = None
            success = True

            try:
                result = f(*args, **kwargs)
                return result

            except Exception as e:
                success = False
                error_info = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                raise

            finally:
                execution_time_ms = (time.time() - start_time) * 1000

                # Build properties
                properties = {
                    "command_name": command_name,
                    "success": success,
                    "execution_time_ms": round(execution_time_ms, 2),
                }

                # Add parameters if tracking enabled
                if track_arguments and ctx.params:
                    arguments = {}
                    options = {}

                    for param_name, param_value in ctx.params.items():
                        param_obj = None
                        for param in ctx.command.params:
                            if param.name == param_name:
                                param_obj = param
                                break

                        if param_obj and isinstance(param_obj, click.Argument):
                            arguments[param_name] = param_value
                        else:
                            options[param_name] = param_value

                    if arguments:
                        properties["arguments"] = arguments

                    if options and track_options:
                        properties["options"] = options

                if error_info:
                    properties.update(error_info)

                # Track event
                event_name = f"cli.{command_name.replace(' ', '.')}"
                try:
                    tracking_client.track(event_name, properties)
                except Exception as e:
                    _logger.debug(f"Failed to track Click command: {e}")

        return wrapper

    # Support both @track_click_command and @track_click_command()
    if func is None:
        return decorator
    else:
        return decorator(func)
