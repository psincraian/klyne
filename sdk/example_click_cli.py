#!/usr/bin/env python3
"""
Example Click CLI with Klyne tracking.

This demonstrates how to integrate Klyne tracking into a real Click CLI application.

Usage:
    python example_click_cli.py --help
    python example_click_cli.py hello --name Alice
    python example_click_cli.py database migrate
    python example_click_cli.py deploy --env production
"""

import sys

# Add SDK to path for testing
sys.path.insert(0, ".")

import click

import klyne

# Initialize Klyne (do this before creating your CLI)
print("🚀 Initializing Klyne...")
client = klyne.init(
    api_key="klyne__HVqua3oQTYeF_w_u_dCh4JmA21KMcwL6j5gmPNsEvU",
    project="example-cli",
    package_version="1.0.0",
    base_url="http://localhost:8000",  # Use local server for testing
    enabled=True,
    debug=True,
)
print(f"✓ Klyne initialized (enabled: {client.is_enabled()})\n")


# Create your Click CLI as usual
@click.group()
def cli():
    """
    Example CLI application with Klyne tracking.

    This CLI demonstrates automatic tracking of all commands,
    options, and arguments without manual instrumentation.
    """
    pass


@cli.command()
@click.option('--name', default='World', help='Name to greet')
@click.option('--count', default=1, type=int, help='Number of times to greet')
def hello(name, count):
    """
    Say hello to someone.

    Example:
        python example_click_cli.py hello --name Alice --count 3
    """
    for i in range(count):
        click.echo(f"Hello {name}! (greeting {i + 1}/{count})")


@cli.group()
def database():
    """Database management commands."""
    pass


@database.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def migrate(dry_run):
    """
    Run database migrations.

    Example:
        python example_click_cli.py database migrate
        python example_click_cli.py database migrate --dry-run
    """
    if dry_run:
        click.echo("🔍 Dry run mode - showing what would be done:")
        click.echo("  • Would create tables")
        click.echo("  • Would run 3 pending migrations")
    else:
        click.echo("🔄 Running database migrations...")
        click.echo("  ✓ Created tables")
        click.echo("  ✓ Ran 3 migrations")
        click.echo("✅ Migrations complete!")


@database.command()
@click.option('--tables', multiple=True, help='Specific tables to seed')
def seed(tables):
    """
    Seed the database with test data.

    Example:
        python example_click_cli.py database seed
        python example_click_cli.py database seed --tables users --tables posts
    """
    if tables:
        click.echo(f"🌱 Seeding specific tables: {', '.join(tables)}")
    else:
        click.echo("🌱 Seeding all tables with test data...")

    click.echo("  ✓ Added 100 users")
    click.echo("  ✓ Added 500 posts")
    click.echo("  ✓ Added 1000 comments")
    click.echo("✅ Database seeded!")


@cli.command()
@click.argument('environment', type=click.Choice(['dev', 'staging', 'production']))
@click.option('--branch', default='main', help='Git branch to deploy')
@click.option('--force', is_flag=True, help='Force deployment')
def deploy(environment, branch, force):
    """
    Deploy the application to an environment.

    Example:
        python example_click_cli.py deploy staging --branch develop
        python example_click_cli.py deploy production --force
    """
    if environment == 'production' and not force:
        click.echo("⚠️  Deploying to production!")
        if not click.confirm('Are you sure?'):
            click.echo("❌ Deployment cancelled")
            return

    click.echo(f"🚀 Deploying to {environment}...")
    click.echo(f"  • Branch: {branch}")
    click.echo(f"  • Environment: {environment}")
    click.echo("  • Running tests...")
    click.echo("  • Building application...")
    click.echo("  • Uploading to server...")
    click.echo("  • Restarting services...")
    click.echo(f"✅ Successfully deployed to {environment}!")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='table')
def status(format):
    """
    Show application status.

    Example:
        python example_click_cli.py status
        python example_click_cli.py status --format json
    """
    if format == 'json':
        click.echo('{"status": "running", "uptime": "24h", "memory": "512MB"}')
    elif format == 'yaml':
        click.echo('status: running\nuptime: 24h\nmemory: 512MB')
    else:
        click.echo("📊 Application Status")
        click.echo("=" * 40)
        click.echo("  Status:  ✅ Running")
        click.echo("  Uptime:  24 hours")
        click.echo("  Memory:  512 MB")
        click.echo("  CPU:     15%")


@cli.command()
@click.argument('value', type=int)
def calculate(value):
    """
    Perform a calculation (demonstrates error tracking).

    This command will fail if value is 0, demonstrating
    how Klyne tracks command failures.

    Example:
        python example_click_cli.py calculate 42
        python example_click_cli.py calculate 0  # Will fail
    """
    try:
        result = 100 / value
        click.echo(f"✓ 100 / {value} = {result}")
    except ZeroDivisionError:
        click.echo("❌ Error: Cannot divide by zero!", err=True)
        raise


# Main entry point with Klyne tracking
if __name__ == '__main__':
    # Use client.track_click() to instrument the CLI
    # This is the only change needed to enable tracking!
    client.track_click(cli)

    # Now just call the CLI normally
    cli()

    # Flush events before exit
    print("\n📤 Flushing Klyne events...")
    client.flush(timeout=2.0)
    print("✓ Events sent to Klyne")
