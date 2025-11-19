# Klyne Click Adapter

Automatic CLI command tracking for Click-based applications.

## Overview

The Klyne Click adapter provides seamless integration with Click CLI applications, automatically tracking all command invocations without requiring manual instrumentation. Simply wrap your CLI with `ClickModule` and all commands, subcommands, options, and arguments are automatically tracked.

## Features

- ✅ **Automatic command tracking** - Track all CLI commands without manual instrumentation
- ✅ **Options and arguments tracking** - Capture command parameters automatically
- ✅ **Nested command groups** - Full support for multi-level command hierarchies
- ✅ **Error tracking** - Automatically track command failures and exceptions
- ✅ **Execution time tracking** - Measure how long commands take to run
- ✅ **Privacy options** - Disable tracking of sensitive arguments/options
- ✅ **Decorator support** - Alternative decorator API for selective tracking
- ✅ **Graceful degradation** - CLI works normally even if Klyne is not configured

## Installation

The Click adapter requires the `click` package:

```bash
pip install klyne click
```

## Quick Start

Here's the simplest way to add Klyne tracking to your Click CLI:

```python
import click
import klyne

# 1. Initialize Klyne
client = klyne.init(api_key="klyne_your_key", project="my-cli")

# 2. Create your Click CLI (as usual)
@click.group()
def cli():
    '''My awesome CLI'''
    pass

@cli.command()
@click.option('--name', default='World')
def hello(name):
    '''Say hello'''
    click.echo(f'Hello {name}!')

# 3. Enable tracking and run your CLI
if __name__ == '__main__':
    client.track_click(cli)
    cli()
```

That's all you need! Every command invocation is now automatically tracked.

## What Gets Tracked

When a user runs a command, Klyne automatically tracks:

- **Command name** - Full command path (e.g., "cli database migrate")
- **Arguments** - Positional arguments passed to the command
- **Options** - Flags and options with their values
- **Success/failure** - Whether the command succeeded or failed
- **Error details** - Exception type and message (if command failed)
- **Execution time** - How long the command took to run (in milliseconds)
- **System info** - OS, Python version, architecture (standard Klyne data)

### Example Tracked Event

```json
{
  "event_name": "cli.database.migrate",
  "command_name": "database migrate",
  "options": {
    "dry_run": false,
    "verbose": true
  },
  "success": true,
  "execution_time_ms": 1234.56,
  "python_version": "3.11.0",
  "os_type": "Linux"
}
```

## Usage Examples

### Basic Command

```python
import click
import klyne

client = klyne.init(api_key="...", project="my-cli")

@click.command()
def deploy():
    '''Deploy the application'''
    click.echo("Deploying...")

if __name__ == '__main__':
    client.track_click(deploy)
    deploy()
```

### Command with Options

```python
client = klyne.init(api_key="...", project="my-cli")

@click.command()
@click.option('--env', type=click.Choice(['dev', 'prod']))
@click.option('--force', is_flag=True)
def deploy(env, force):
    '''Deploy to environment'''
    click.echo(f"Deploying to {env}...")

# Tracks: command name, env value, force flag
client.track_click(deploy)
deploy()
```

### Command with Arguments

```python
client = klyne.init(api_key="...", project="my-cli")

@click.command()
@click.argument('filename')
@click.option('--format', default='json')
def process(filename, format):
    '''Process a file'''
    click.echo(f"Processing {filename} as {format}")

# Tracks: filename argument and format option
client.track_click(process)
process()
```

### Command Groups (Multi-command CLI)

```python
client = klyne.init(api_key="...", project="my-cli")

@click.group()
def cli():
    '''Multi-command CLI'''
    pass

@cli.command()
def status():
    '''Show status'''
    click.echo("Status: OK")

@cli.command()
@click.option('--force', is_flag=True)
def restart(force):
    '''Restart service'''
    click.echo("Restarting...")

# Instrument the entire group - all commands are tracked
client.track_click(cli)
cli()
```

### Nested Command Groups

```python
client = klyne.init(api_key="...", project="my-cli")

@click.group()
def cli():
    '''Main CLI'''
    pass

@cli.group()
def database():
    '''Database commands'''
    pass

@database.command()
def migrate():
    '''Run migrations'''
    click.echo("Migrating...")

@database.command()
def seed():
    '''Seed database'''
    click.echo("Seeding...")

# Command path is tracked: "cli database migrate"
client.track_click(cli)
cli()
```

### Error Tracking

```python
client = klyne.init(api_key="...", project="my-cli")

@click.command()
@click.argument('value', type=int)
def divide(value):
    '''Divide 100 by value'''
    result = 100 / value  # Will fail if value is 0
    click.echo(f"Result: {result}")

# Automatically tracks exceptions:
# {
#   "success": false,
#   "error_type": "ZeroDivisionError",
#   "error_message": "division by zero"
# }
client.track_click(divide)
divide()
```

## Privacy and Security

### Disable Tracking of Sensitive Data

If your commands accept sensitive data (passwords, tokens, etc.), you can disable tracking of arguments and options:

```python
client = klyne.init(api_key="...", project="my-cli")

@click.command()
@click.argument('username')
@click.option('--password')
def login(username, password):
    '''Login to service'''
    # ... authenticate ...
    pass

# Don't track arguments or options (only command name and success/failure)
client.track_click(
    login,
    track_arguments=False,  # Don't track username
    track_options=False      # Don't track password
)
login()
```

### Selective Tracking with Decorator

For fine-grained control, use the `@track_click_command` decorator on specific commands:

```python
from klyne.click_adapter import track_click_command

@click.command()
@click.option('--verbose', is_flag=True)
@track_click_command  # Only this command is tracked
def deploy(verbose):
    '''Deploy application'''
    pass

@click.command()
def login():
    '''Login (NOT tracked)'''
    pass
```

## Advanced Configuration

### Using a Custom Client

If you're managing multiple Klyne clients, you can pass a specific client:

```python
import klyne
from klyne.click_adapter import ClickModule

# Create a custom client
client = klyne.init(
    api_key="klyne_your_key",
    project="my-cli",
    package_version="2.0.0"
)

# Use the custom client
ClickModule(cli, client=client)()
```

### Disabling Tracking at Runtime

```python
import klyne

# Initialize normally
klyne.init(api_key="...", project="...")

# Disable tracking (e.g., for local development)
klyne.disable()

# Commands will not be tracked
ClickModule(cli)()

# Re-enable when needed
klyne.enable()
```

## Best Practices

1. **Initialize Early** - Call `klyne.init()` before creating `ClickModule`
2. **Wrap at Entry Point** - Wrap your CLI at the `if __name__ == '__main__'` block
3. **Privacy First** - Disable tracking for sensitive commands
4. **Flush on Exit** - Call `klyne.flush()` before program exit for clean shutdown
5. **Version Your CLI** - Pass `package_version` to track usage across versions

## Complete Example

```python
#!/usr/bin/env python3
"""
My CLI application with Klyne tracking.
"""
import click
import klyne

# Initialize Klyne
client = klyne.init(
    api_key="klyne_your_api_key",
    project="my-cli",
    package_version="1.0.0"
)

@click.group()
def cli():
    '''My CLI application'''
    pass

@cli.command()
@click.option('--name', default='World')
def hello(name):
    '''Say hello'''
    click.echo(f'Hello {name}!')

@cli.group()
def database():
    '''Database commands'''
    pass

@database.command()
def migrate():
    '''Run migrations'''
    click.echo("Running migrations...")

@database.command()
def seed():
    '''Seed database'''
    click.echo("Seeding database...")

if __name__ == '__main__':
    # Use client.track_click() to enable tracking
    client.track_click(cli)

    # Now call your CLI normally
    cli()

    # Flush events before exit
    client.flush(timeout=2.0)
```

## API Reference

### client.track_click()

**Recommended API** - Use this method on your KlyneClient instance:

```python
client.track_click(
    cli,                      # Click Group or Command
    track_arguments=True,     # Track command arguments
    track_options=True,       # Track command options
)
```

**Parameters:**
- `cli` - Click Group or Command instance to instrument
- `track_arguments` - Whether to track command arguments (default: True)
- `track_options` - Whether to track command options/flags (default: True)

**Returns:** None (instruments the CLI in-place)

**Example:**
```python
client = klyne.init(api_key="...", project="my-cli")

@click.group()
def cli():
    pass

if __name__ == '__main__':
    client.track_click(cli)
    cli()
```

### ClickModule (Alternative API)

For backward compatibility, you can also use `ClickModule` directly:

```python
ClickModule(
    cli,                      # Click Group or Command
    track_arguments=True,     # Track command arguments
    track_options=True,       # Track command options
    client=None               # Optional KlyneClient instance
)
```

**Parameters:**
- `cli` - Click Group or Command instance to wrap
- `track_arguments` - Whether to track command arguments (default: True)
- `track_options` - Whether to track command options/flags (default: True)
- `client` - Optional KlyneClient instance (uses default client if not provided)

**Returns:** Callable wrapper that can be invoked like the original CLI

### track_click_command

```python
@track_click_command(
    track_arguments=True,     # Track command arguments
    track_options=True,       # Track command options
    client=None               # Optional KlyneClient instance
)
```

Decorator for tracking individual Click commands.

**Parameters:**
- Same as ClickModule

**Usage:**
```python
@click.command()
@track_click_command
def my_command():
    pass
```

## Troubleshooting

### Commands Not Being Tracked

**Problem:** Commands run but no events appear in Klyne dashboard

**Solutions:**
1. Ensure `klyne.init()` is called before `ClickModule`
2. Check that tracking is enabled: `klyne.is_enabled()`
3. Call `klyne.flush()` before program exit
4. Verify your API key is correct

### ImportError: No module named 'click'

**Problem:** Click is not installed

**Solution:** Install Click: `pip install click`

### Warnings About Client Not Initialized

**Problem:** You see "Klyne not initialized" warnings

**Solution:** Call `klyne.init()` before creating `ClickModule`:

```python
# ✅ Correct order
klyne.init(api_key="...", project="...")
ClickModule(cli)()

# ❌ Wrong order
ClickModule(cli)()
klyne.init(api_key="...", project="...")
```

## Testing

The Click adapter includes comprehensive tests:

```bash
python test_click_adapter.py
```

## Examples

See `example_click_cli.py` for a complete working example with multiple command types.

## Support

- Documentation: https://www.klyne.dev/docs
- Issues: https://github.com/psincraian/klyne/issues
- Email: hello@klyne.dev
