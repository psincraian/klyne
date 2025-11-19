#!/usr/bin/env python3
"""
Comprehensive tests for Klyne Click adapter.

Tests both ClickModule and track_click_command decorator.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Set testing environment
os.environ["KLYNE_TESTING"] = "true"

# Add SDK to path
sys.path.insert(0, ".")

import click
from click.testing import CliRunner

import klyne
from klyne.click_adapter import ClickModule, track_click_command


def test_click_module_basic():
    """Test basic ClickModule functionality with simple command."""
    print("\n1. Testing ClickModule with basic command...")

    # Create a mock client to verify tracking
    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    # Create a simple Click command
    @click.command()
    def hello():
        """Simple hello command."""
        click.echo("Hello!")

    # Wrap with ClickModule
    cli_wrapped = ClickModule(hello, client=mock_client)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli)

    assert result.exit_code == 0
    assert "Hello!" in result.output

    # Verify tracking was called
    assert mock_client.track.called
    call_args = mock_client.track.call_args

    # Check event name and properties
    event_name = call_args[0][0]
    properties = call_args[0][1]

    assert "cli" in event_name
    assert "hello" in event_name
    assert properties["success"] is True
    assert "execution_time_ms" in properties
    assert properties["execution_time_ms"] >= 0

    print("   ✓ Basic command tracking works")


def test_click_module_with_options():
    """Test ClickModule with command options."""
    print("\n2. Testing ClickModule with options...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    @click.option('--name', default='World', help='Name to greet')
    @click.option('--count', default=1, type=int, help='Number of greetings')
    def hello(name, count):
        """Greet someone multiple times."""
        for _ in range(count):
            click.echo(f"Hello {name}!")

    cli_wrapped = ClickModule(hello, client=mock_client)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli, ['--name', 'Alice', '--count', '3'])

    assert result.exit_code == 0
    assert result.output.count("Hello Alice!") == 3

    # Verify tracking
    assert mock_client.track.called
    properties = mock_client.track.call_args[0][1]

    assert properties["success"] is True
    assert "options" in properties
    assert properties["options"]["name"] == "Alice"
    assert properties["options"]["count"] == 3

    print("   ✓ Command options tracked correctly")


def test_click_module_with_arguments():
    """Test ClickModule with command arguments."""
    print("\n3. Testing ClickModule with arguments...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    @click.argument('filename')
    @click.option('--format', default='json')
    def process(filename, format):
        """Process a file."""
        click.echo(f"Processing {filename} as {format}")

    cli_wrapped = ClickModule(process, client=mock_client)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli, ['data.csv', '--format', 'csv'])

    assert result.exit_code == 0
    assert "Processing data.csv as csv" in result.output

    # Verify tracking
    properties = mock_client.track.call_args[0][1]

    assert "arguments" in properties
    assert properties["arguments"]["filename"] == "data.csv"
    assert "options" in properties
    assert properties["options"]["format"] == "csv"

    print("   ✓ Command arguments tracked correctly")


def test_click_module_with_group():
    """Test ClickModule with Click Group (multi-command CLI)."""
    print("\n4. Testing ClickModule with command groups...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.group()
    def cli():
        """Multi-command CLI."""
        pass

    @cli.command()
    def deploy():
        """Deploy the application."""
        click.echo("Deploying...")

    @cli.command()
    @click.option('--env', default='dev')
    def status(env):
        """Check status."""
        click.echo(f"Status for {env}")

    # Wrap the group
    cli_wrapped = ClickModule(cli, client=mock_client)

    runner = CliRunner()

    # Test deploy command
    result = runner.invoke(cli_wrapped.cli, ['deploy'])
    assert result.exit_code == 0
    assert "Deploying..." in result.output

    # Check tracking for deploy
    deploy_call = mock_client.track.call_args_list[0]
    deploy_event = deploy_call[0][0]
    deploy_props = deploy_call[0][1]

    assert "deploy" in deploy_event
    assert deploy_props["success"] is True

    # Test status command
    result = runner.invoke(cli_wrapped.cli, ['status', '--env', 'prod'])
    assert result.exit_code == 0
    assert "Status for prod" in result.output

    # Check tracking for status
    status_call = mock_client.track.call_args_list[1]
    status_event = status_call[0][0]
    status_props = status_call[0][1]

    assert "status" in status_event
    assert status_props["options"]["env"] == "prod"

    print("   ✓ Command groups tracked correctly")


def test_click_module_nested_groups():
    """Test ClickModule with nested command groups."""
    print("\n5. Testing ClickModule with nested groups...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.group()
    def cli():
        """Main CLI."""
        pass

    @cli.group()
    def database():
        """Database commands."""
        pass

    @database.command()
    def migrate():
        """Run migrations."""
        click.echo("Running migrations...")

    @database.command()
    def seed():
        """Seed database."""
        click.echo("Seeding database...")

    cli_wrapped = ClickModule(cli, client=mock_client)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli, ['database', 'migrate'])

    assert result.exit_code == 0
    assert "Running migrations..." in result.output

    # Verify full command path is tracked
    event_name = mock_client.track.call_args[0][0]
    properties = mock_client.track.call_args[0][1]

    # Command name should include full path
    assert "database" in properties["command_name"]
    assert "migrate" in properties["command_name"]

    print("   ✓ Nested groups tracked with full command path")


def test_click_module_error_handling():
    """Test ClickModule tracks errors correctly."""
    print("\n6. Testing error handling and tracking...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    @click.argument('value', type=int)
    def divide(value):
        """Divide 100 by value."""
        result = 100 / value
        click.echo(f"Result: {result}")

    cli_wrapped = ClickModule(divide, client=mock_client)

    runner = CliRunner()

    # Test with zero (will raise error)
    result = runner.invoke(cli_wrapped.cli, ['0'])

    # Command should fail
    assert result.exit_code != 0

    # Verify error was tracked
    properties = mock_client.track.call_args[0][1]

    assert properties["success"] is False
    assert "error_type" in properties
    assert properties["error_type"] == "ZeroDivisionError"
    assert "error_message" in properties

    print("   ✓ Errors tracked correctly")


def test_track_click_command_decorator():
    """Test track_click_command decorator."""
    print("\n7. Testing track_click_command decorator...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    @click.option('--message', default='Hello')
    @track_click_command(client=mock_client)
    def greet(message):
        """Greet with custom message."""
        click.echo(message)

    runner = CliRunner()
    result = runner.invoke(greet, ['--message', 'Hi there!'])

    assert result.exit_code == 0
    assert "Hi there!" in result.output

    # Verify tracking
    assert mock_client.track.called
    properties = mock_client.track.call_args[0][1]

    assert properties["success"] is True
    assert properties["options"]["message"] == "Hi there!"

    print("   ✓ Decorator tracking works")


def test_click_module_disabled_tracking():
    """Test that tracking is skipped when client is disabled."""
    print("\n8. Testing disabled tracking...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = False

    @click.command()
    def hello():
        click.echo("Hello!")

    cli_wrapped = ClickModule(hello, client=mock_client)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli)

    assert result.exit_code == 0

    # Tracking should not be called when disabled
    assert not mock_client.track.called

    print("   ✓ Tracking skipped when disabled")


def test_click_module_no_client():
    """Test ClickModule works without Klyne client (logs warning)."""
    print("\n9. Testing without Klyne client...")

    @click.command()
    def hello():
        click.echo("Hello!")

    # Create wrapper without client (should warn but still work)
    with patch('klyne.client._default_client', None):
        cli_wrapped = ClickModule(hello, client=None)

        runner = CliRunner()
        result = runner.invoke(cli_wrapped.cli)

        assert result.exit_code == 0
        assert "Hello!" in result.output

    print("   ✓ Works without client (graceful degradation)")


def test_click_module_privacy_options():
    """Test privacy options (disable argument/option tracking)."""
    print("\n10. Testing privacy options...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    @click.argument('secret')
    @click.option('--password', default='')
    def login(secret, password):
        """Login command with sensitive data."""
        click.echo("Logged in")

    # Create wrapper with tracking disabled
    cli_wrapped = ClickModule(
        login,
        client=mock_client,
        track_arguments=False,
        track_options=False
    )

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli, ['my-secret', '--password', 'pass123'])

    assert result.exit_code == 0

    # Verify sensitive data is NOT tracked
    properties = mock_client.track.call_args[0][1]

    assert "arguments" not in properties
    assert "options" not in properties
    assert properties["success"] is True

    print("   ✓ Privacy options work (sensitive data not tracked)")


def test_integration_with_klyne_init():
    """Test integration with real Klyne initialization."""
    print("\n11. Testing integration with klyne.init()...")

    # Initialize Klyne
    client = klyne.init(
        api_key="test_key",
        project="test-cli",
        package_version="1.0.0",
        enabled=False  # Disable to avoid network calls
    )

    # Enable for testing
    client.enable()

    @click.command()
    @click.option('--count', default=1, type=int)
    def test_cmd(count):
        """Test command."""
        click.echo(f"Count: {count}")

    cli_wrapped = ClickModule(test_cmd)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli, ['--count', '5'])

    assert result.exit_code == 0
    assert "Count: 5" in result.output

    print("   ✓ Integration with klyne.init() works")


def test_execution_time_tracking():
    """Test that execution time is tracked accurately."""
    print("\n12. Testing execution time tracking...")

    mock_client = MagicMock()
    mock_client.is_enabled.return_value = True

    @click.command()
    def slow_command():
        """Command that takes some time."""
        import time
        time.sleep(0.1)  # Sleep for 100ms
        click.echo("Done")

    cli_wrapped = ClickModule(slow_command, client=mock_client)

    runner = CliRunner()
    result = runner.invoke(cli_wrapped.cli)

    assert result.exit_code == 0

    # Verify execution time is tracked and reasonable
    properties = mock_client.track.call_args[0][1]

    assert "execution_time_ms" in properties
    # Should be at least 100ms (allowing for some variance)
    assert properties["execution_time_ms"] >= 90

    print("   ✓ Execution time tracked accurately")


def test_client_track_click_api():
    """Test the new client.track_click() API."""
    print("\n13. Testing client.track_click() API...")

    # Initialize Klyne client
    client = klyne.init(
        api_key="test_key",
        project="test-cli",
        package_version="1.0.0",
        enabled=False
    )

    # Enable for testing
    client.enable()

    @click.command()
    @click.option('--message', default='Hello')
    def greet(message):
        """Greet command."""
        click.echo(message)

    # Use the new client.track_click() API
    client.track_click(greet)

    runner = CliRunner()
    result = runner.invoke(greet, ['--message', 'Hi!'])

    assert result.exit_code == 0
    assert "Hi!" in result.output

    print("   ✓ client.track_click() API works")


def test_client_track_click_with_group():
    """Test client.track_click() with command groups."""
    print("\n14. Testing client.track_click() with groups...")

    client = klyne.init(
        api_key="test_key",
        project="test-cli-2",
        package_version="1.0.0",
        enabled=False
    )

    client.enable()

    @click.group()
    def cli():
        """Main CLI."""
        pass

    @cli.command()
    def status():
        """Show status."""
        click.echo("Status: OK")

    # Use the new API with a group
    client.track_click(cli)

    runner = CliRunner()
    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0
    assert "Status: OK" in result.output

    print("   ✓ client.track_click() works with groups")


def main():
    """Run all tests."""
    print("🧪 Klyne Click Adapter Tests")
    print("=" * 50)

    try:
        test_click_module_basic()
        test_click_module_with_options()
        test_click_module_with_arguments()
        test_click_module_with_group()
        test_click_module_nested_groups()
        test_click_module_error_handling()
        test_track_click_command_decorator()
        test_click_module_disabled_tracking()
        test_click_module_no_client()
        test_click_module_privacy_options()
        test_integration_with_klyne_init()
        test_execution_time_tracking()
        test_client_track_click_api()
        test_client_track_click_with_group()

        print("\n✅ All Click adapter tests passed!")
        print("\nClick Adapter Features:")
        print("  • Automatic command tracking: ✓")
        print("  • Options and arguments tracking: ✓")
        print("  • Nested command groups: ✓")
        print("  • Error tracking: ✓")
        print("  • Execution time tracking: ✓")
        print("  • Privacy options: ✓")
        print("  • Decorator support: ✓")
        print("  • Graceful degradation: ✓")
        print("  • client.track_click() API: ✓")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
