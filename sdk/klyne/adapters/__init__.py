"""
CLI framework adapters for Klyne analytics.

Provides easy integration with popular Python CLI frameworks:
- Click: `track_click(group, api_key, project)`
- Typer: `track_typer(app, api_key, project)`
- argparse: `track_argparse(parser, api_key, project)`

Each adapter allows adding analytics tracking with a single line of code.

Example (Click):
    import click
    from klyne.adapters import track_click

    @click.group()
    def cli():
        pass

    track_click(cli, api_key="klyne_...", project="my-cli")

Example (Typer):
    import typer
    from klyne.adapters import track_typer

    app = typer.Typer()
    track_typer(app, api_key="klyne_...", project="my-cli")

Example (argparse):
    import argparse
    from klyne.adapters import track_argparse

    parser = argparse.ArgumentParser(prog='my-cli')
    track_argparse(parser, api_key="klyne_...", project="my-cli")
"""

from .argparse import track_argparse
from .base import BaseCLIAdapter, CommandExecution
from .click import track_click
from .typer import track_typer

__all__ = [
    "track_click",
    "track_typer",
    "track_argparse",
    "BaseCLIAdapter",
    "CommandExecution",
]
