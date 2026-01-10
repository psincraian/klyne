#!/usr/bin/env python3
"""
Example: Using Klyne with Click CLI framework.

This demonstrates how to add analytics tracking to a Click CLI app
with just one line of code.

Usage:
    python click_example.py install --name my-package
    python click_example.py uninstall --name my-package
    python click_example.py --help
"""

import click

from klyne.adapters import track_click


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose):
    """My awesome CLI tool."""
    if verbose:
        click.echo("Verbose mode enabled")


# Add Klyne tracking with a single line
track_click(cli, api_key="klyne_example_key", project="my-cli", debug=True)


@cli.command()
@click.option("--name", "-n", required=True, help="Package name to install")
@click.option("--version", "-v", default="latest", help="Package version")
def install(name, version):
    """Install a package."""
    click.echo(f"Installing {name}@{version}...")
    click.echo("Done!")


@cli.command()
@click.option("--name", "-n", required=True, help="Package name to uninstall")
@click.option("--force", "-f", is_flag=True, help="Force uninstall")
def uninstall(name, force):
    """Uninstall a package."""
    if force:
        click.echo(f"Force uninstalling {name}...")
    else:
        click.echo(f"Uninstalling {name}...")
    click.echo("Done!")


@cli.command()
def list():
    """List installed packages."""
    click.echo("Installed packages:")
    click.echo("  - package-a@1.0.0")
    click.echo("  - package-b@2.3.1")


if __name__ == "__main__":
    cli()
