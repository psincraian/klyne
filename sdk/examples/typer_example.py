#!/usr/bin/env python3
"""
Example: Using Klyne with Typer CLI framework.

This demonstrates how to add analytics tracking to a Typer CLI app
with just one line of code.

Usage:
    python typer_example.py install my-package
    python typer_example.py uninstall my-package
    python typer_example.py --help
"""

from typing import Optional

import typer

from klyne.adapters import track_typer

app = typer.Typer(help="My awesome CLI tool.")

# Add Klyne tracking with a single line
track_typer(app, api_key="klyne_example_key", project="my-cli", debug=True)


@app.command()
def install(
    name: str = typer.Argument(..., help="Package name to install"),
    version: str = typer.Option("latest", "--version", "-v", help="Package version"),
):
    """Install a package."""
    typer.echo(f"Installing {name}@{version}...")
    typer.echo("Done!")


@app.command()
def uninstall(
    name: str = typer.Argument(..., help="Package name to uninstall"),
    force: bool = typer.Option(False, "--force", "-f", help="Force uninstall"),
):
    """Uninstall a package."""
    if force:
        typer.echo(f"Force uninstalling {name}...")
    else:
        typer.echo(f"Uninstalling {name}...")
    typer.echo("Done!")


@app.command("list")
def list_packages():
    """List installed packages."""
    typer.echo("Installed packages:")
    typer.echo("  - package-a@1.0.0")
    typer.echo("  - package-b@2.3.1")


if __name__ == "__main__":
    app()
