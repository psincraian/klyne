#!/usr/bin/env python3
"""
Tests for CLI framework adapters.

Tests the track_click, track_typer, and track_argparse functions
to ensure they properly wrap CLI frameworks and track executions.
"""

import argparse
import time
from unittest.mock import MagicMock, patch

import pytest

from klyne.adapters.base import BaseCLIAdapter, CommandExecution, _detect_package_version


class TestCommandExecution:
    """Tests for CommandExecution dataclass."""

    def test_creation(self):
        """Test creating a CommandExecution instance."""
        execution = CommandExecution(command_name="test")
        assert execution.command_name == "test"
        assert execution.subcommand is None
        assert execution.success is True
        assert execution.exit_code == 0

    def test_complete_success(self):
        """Test completing a successful execution."""
        execution = CommandExecution(command_name="test")
        time.sleep(0.01)  # Small delay
        execution.complete(success=True, exit_code=0)

        assert execution.success is True
        assert execution.exit_code == 0
        assert execution.duration_ms is not None
        assert execution.duration_ms > 0

    def test_complete_failure(self):
        """Test completing a failed execution."""
        execution = CommandExecution(command_name="test")
        execution.complete(
            success=False,
            exit_code=1,
            error_type="ValueError",
            error_message="Something went wrong",
        )

        assert execution.success is False
        assert execution.exit_code == 1
        assert execution.error_type == "ValueError"
        assert execution.error_message == "Something went wrong"


class TestBaseCLIAdapter:
    """Tests for BaseCLIAdapter class."""

    def test_init_with_defaults(self):
        """Test adapter initialization with default values."""
        adapter = BaseCLIAdapter(api_key="test_key", project="test-project")

        assert adapter._api_key == "test_key"
        assert adapter._project == "test-project"
        assert adapter._enabled is True
        assert adapter._track_args is False

    def test_init_with_custom_version(self):
        """Test adapter with explicit package version."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            package_version="1.2.3",
        )

        assert adapter._package_version == "1.2.3"

    def test_sanitize_args_disabled(self):
        """Test that args are not tracked when track_args=False."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            track_args=False,
        )

        result = adapter._sanitize_args({"name": "value", "password": "secret"})
        assert result == {}

    def test_sanitize_args_enabled(self):
        """Test that args are tracked when track_args=True."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            track_args=True,
        )

        result = adapter._sanitize_args({"name": "value", "count": 42})
        assert result == {"name": "value", "count": 42}

    def test_sanitize_args_redacts_sensitive(self):
        """Test that sensitive args are redacted."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            track_args=True,
        )

        result = adapter._sanitize_args({
            "name": "value",
            "password": "secret123",
            "api_key": "key123",
            "token": "tok123",
        })

        assert result["name"] == "value"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"

    def test_sanitize_args_custom_sensitive(self):
        """Test that custom sensitive args are redacted."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            track_args=True,
            sensitive_args=["my_secret_field"],
        )

        result = adapter._sanitize_args({
            "name": "value",
            "my_secret_field": "secret",
        })

        assert result["name"] == "value"
        assert result["my_secret_field"] == "[REDACTED]"

    def test_sanitize_args_handles_complex_types(self):
        """Test that complex types are simplified."""
        adapter = BaseCLIAdapter(
            api_key="test_key",
            project="test-project",
            track_args=True,
        )

        result = adapter._sanitize_args({
            "name": "value",
            "file": open.__class__,  # Not a simple type
            "items": [1, 2, 3],
        })

        assert result["name"] == "value"
        assert "<type>" in result["file"]
        assert result["items"] == [1, 2, 3]


class TestDetectPackageVersion:
    """Tests for version detection."""

    def test_detect_unknown_package(self):
        """Test detecting version of unknown package."""
        version = _detect_package_version("nonexistent-package-12345")
        assert version == "unknown"


class TestTrackClick:
    """Tests for Click adapter."""

    def test_track_click_imports_correctly(self):
        """Test that track_click can be imported."""
        from klyne.adapters import track_click

        assert callable(track_click)

    def test_track_click_with_group(self):
        """Test tracking a Click group."""
        try:
            import click
            from click.testing import CliRunner
        except ImportError:
            pytest.skip("Click not installed")

        from klyne.adapters import track_click

        @click.group()
        def cli():
            pass

        @cli.command()
        def hello():
            click.echo("Hello!")

        # Track the CLI
        with patch("klyne.adapters.click.ClickAdapter._track_execution") as mock_track:
            track_click(cli, api_key="test", project="test-cli")

            runner = CliRunner()
            result = runner.invoke(cli, ["hello"])

            assert result.exit_code == 0
            assert "Hello!" in result.output

    def test_track_click_returns_same_group(self):
        """Test that track_click returns the same group."""
        try:
            import click
        except ImportError:
            pytest.skip("Click not installed")

        from klyne.adapters import track_click

        @click.group()
        def cli():
            pass

        result = track_click(cli, api_key="test", project="test-cli")
        assert result is cli


class TestTrackTyper:
    """Tests for Typer adapter."""

    def test_track_typer_imports_correctly(self):
        """Test that track_typer can be imported."""
        from klyne.adapters import track_typer

        assert callable(track_typer)

    def test_track_typer_with_app(self):
        """Test tracking a Typer app."""
        try:
            import typer
            from typer.testing import CliRunner
        except ImportError:
            pytest.skip("Typer not installed")

        from klyne.adapters import track_typer

        app = typer.Typer()

        @app.command()
        def hello():
            typer.echo("Hello!")

        # Track the app
        with patch("klyne.adapters.typer.TyperAdapter._track_execution"):
            track_typer(app, api_key="test", project="test-cli")

            runner = CliRunner()
            result = runner.invoke(app, ["hello"])

            assert result.exit_code == 0

    def test_track_typer_returns_same_app(self):
        """Test that track_typer returns the same app."""
        try:
            import typer
        except ImportError:
            pytest.skip("Typer not installed")

        from klyne.adapters import track_typer

        app = typer.Typer()

        result = track_typer(app, api_key="test", project="test-cli")
        assert result is app


class TestTrackArgparse:
    """Tests for argparse adapter."""

    def test_track_argparse_imports_correctly(self):
        """Test that track_argparse can be imported."""
        from klyne.adapters import track_argparse

        assert callable(track_argparse)

    def test_track_argparse_with_parser(self):
        """Test tracking an argparse parser."""
        from klyne.adapters import track_argparse

        parser = argparse.ArgumentParser(prog="test-cli")
        parser.add_argument("command", choices=["install", "uninstall"])

        with patch("klyne.adapters.argparse.ArgparseAdapter._track_execution") as mock_track:
            track_argparse(parser, api_key="test", project="test-cli")

            args = parser.parse_args(["install"])
            assert args.command == "install"

            # Verify tracking was called
            assert mock_track.called

    def test_track_argparse_returns_same_parser(self):
        """Test that track_argparse returns the same parser."""
        from klyne.adapters import track_argparse

        parser = argparse.ArgumentParser(prog="test-cli")
        result = track_argparse(parser, api_key="test", project="test-cli")
        assert result is parser

    def test_track_argparse_handles_subparsers(self):
        """Test tracking with subparsers."""
        from klyne.adapters import track_argparse

        parser = argparse.ArgumentParser(prog="test-cli")
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("install")
        subparsers.add_parser("uninstall")

        with patch("klyne.adapters.argparse.ArgparseAdapter._track_execution") as mock_track:
            track_argparse(parser, api_key="test", project="test-cli")

            args = parser.parse_args(["install"])
            assert args.command == "install"

            # Verify subcommand was captured
            call_args = mock_track.call_args
            execution = call_args[0][0]
            assert execution.subcommand == "install"


class TestAdaptersModuleImport:
    """Tests for adapters module imports."""

    def test_import_from_adapters(self):
        """Test importing from klyne.adapters."""
        from klyne.adapters import track_argparse, track_click, track_typer

        assert callable(track_click)
        assert callable(track_typer)
        assert callable(track_argparse)

    def test_import_from_klyne(self):
        """Test importing adapters via klyne module."""
        import klyne

        assert hasattr(klyne, "adapters")
        assert hasattr(klyne.adapters, "track_click")
        assert hasattr(klyne.adapters, "track_typer")
        assert hasattr(klyne.adapters, "track_argparse")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
