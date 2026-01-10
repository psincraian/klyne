"""
argparse CLI framework adapter for Klyne analytics.

Provides the `track_argparse` function to add analytics tracking to argparse
CLI applications with a single line of code.

Example:
    import argparse
    from klyne.adapters import track_argparse

    parser = argparse.ArgumentParser(prog='my-cli')
    parser.add_argument('command', choices=['install', 'uninstall'])
    track_argparse(parser, api_key="klyne_...", project="my-cli")

    args = parser.parse_args()
"""

import functools
import logging
import time
from typing import List, Optional

from .base import BaseCLIAdapter, CommandExecution

_logger = logging.getLogger(__name__)


class ArgparseAdapter(BaseCLIAdapter):
    """argparse-specific adapter implementation."""

    pass


def track_argparse(
    parser,
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
    Add Klyne analytics tracking to an argparse ArgumentParser.

    This function wraps the parser's parse_args() method to automatically track:
    - Command name (from parser.prog)
    - Subcommand (from 'command' or 'subcommand' dest)
    - Execution duration
    - Success/failure status
    - Exit codes
    - Error information (on failure)
    - Command arguments (if track_args=True)

    Args:
        parser: ArgumentParser instance to track
        api_key: Klyne API key
        project: Project name for analytics
        package_version: Version of your CLI tool (auto-detected if None)
        base_url: Klyne API URL
        enabled: Enable/disable tracking
        debug: Enable debug logging
        track_args: Whether to track command arguments
        sensitive_args: Additional argument names to always redact

    Returns:
        The same parser with tracking added

    Example:
        import argparse
        from klyne.adapters import track_argparse

        parser = argparse.ArgumentParser(prog='my-cli')
        subparsers = parser.add_subparsers(dest='command')
        subparsers.add_parser('install')
        subparsers.add_parser('uninstall')

        track_argparse(parser, api_key="klyne_...", project="my-cli")

        args = parser.parse_args()
    """
    adapter = ArgparseAdapter(
        api_key=api_key,
        project=project,
        package_version=package_version,
        base_url=base_url,
        enabled=enabled,
        debug=debug,
        track_args=track_args,
        sensitive_args=sensitive_args,
    )

    # Store original parse_args
    original_parse_args = parser.parse_args

    @functools.wraps(original_parse_args)
    def tracked_parse_args(args=None, namespace=None):
        """Wrapped parse_args that tracks execution."""
        start_time = time.perf_counter()
        command_name = parser.prog or "cli"

        execution = CommandExecution(
            command_name=command_name,
            start_time=start_time,
        )

        try:
            result = original_parse_args(args, namespace)

            # Extract subcommand from common patterns
            args_dict = vars(result) if result else {}
            subcommand = (
                args_dict.get("command")
                or args_dict.get("subcommand")
                or args_dict.get("cmd")
                or args_dict.get("action")
            )

            execution.subcommand = subcommand
            execution.args = adapter._sanitize_args(args_dict)
            execution.complete(success=True, exit_code=0)

            adapter._track_execution(execution)
            return result

        except SystemExit as e:
            # argparse calls sys.exit on errors (--help, --version, parse errors)
            exit_code = e.code if isinstance(e.code, int) else 1
            execution.complete(
                success=(exit_code == 0),
                exit_code=exit_code,
            )

            try:
                adapter._track_execution(execution)
            except Exception:
                pass

            raise

        except Exception as e:
            execution.complete(
                success=False,
                exit_code=1,
                error_type=type(e).__name__,
                error_message=str(e),
            )

            try:
                adapter._track_execution(execution)
            except Exception:
                pass

            raise

    # Replace parse_args
    parser.parse_args = tracked_parse_args

    return parser
