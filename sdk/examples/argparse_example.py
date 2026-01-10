#!/usr/bin/env python3
"""
Example: Using Klyne with argparse CLI framework.

This demonstrates how to add analytics tracking to an argparse CLI app
with just one line of code.

Usage:
    python argparse_example.py install --name my-package
    python argparse_example.py uninstall --name my-package
    python argparse_example.py --help
"""

import argparse

from klyne.adapters import track_argparse


def main():
    parser = argparse.ArgumentParser(
        prog="my-cli",
        description="My awesome CLI tool.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument("--name", "-n", required=True, help="Package name")
    install_parser.add_argument(
        "--version", "-v", default="latest", help="Package version"
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a package")
    uninstall_parser.add_argument("--name", "-n", required=True, help="Package name")
    uninstall_parser.add_argument(
        "--force", "-f", action="store_true", help="Force uninstall"
    )

    # List command
    subparsers.add_parser("list", help="List installed packages")

    # Add Klyne tracking with a single line
    track_argparse(parser, api_key="klyne_example_key", project="my-cli", debug=True)

    # Parse args (tracking happens automatically)
    args = parser.parse_args()

    # Handle commands
    if args.command == "install":
        print(f"Installing {args.name}@{args.version}...")
        print("Done!")
    elif args.command == "uninstall":
        if args.force:
            print(f"Force uninstalling {args.name}...")
        else:
            print(f"Uninstalling {args.name}...")
        print("Done!")
    elif args.command == "list":
        print("Installed packages:")
        print("  - package-a@1.0.0")
        print("  - package-b@2.3.1")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
