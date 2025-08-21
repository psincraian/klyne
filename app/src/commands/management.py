#!/usr/bin/env python3
"""
Management CLI commands for Klyne application.

Usage:
    python -m src.commands.management <command> [args...]

Commands:
    sync-polar              - Run full Polar package sync for all users
    sync-polar-user <id>    - Run Polar package sync for specific user
    help                    - Show this help message

Examples:
    python -m src.commands.management sync-polar
    python -m src.commands.management sync-polar-user 123
"""

import asyncio
import sys
import logging
# typing imports removed as they're not used in this file

from src.commands.sync_polar_packages import sync_all_users_packages, sync_single_user_packages
from src.core.config import settings

# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


async def main():
    """Main entry point for management commands."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "help" or command == "--help" or command == "-h":
        print_help()
        return
    
    elif command == "sync-polar":
        await handle_sync_polar()
    
    elif command == "sync-polar-user":
        await handle_sync_polar_user()
    
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)


async def handle_sync_polar():
    """Handle the sync-polar command."""
    print("🔄 Starting Polar package sync for all users...")
    
    try:
        results = await sync_all_users_packages()
        
        print("✅ Sync completed!")
        print(f"   Total users: {results['total_users']}")
        print(f"   Successful: {results['successful_syncs']}")
        print(f"   Failed: {results['failed_syncs']}")
        print(f"   Duration: {results['duration_seconds']:.2f}s")
        
        if results['errors']:
            print("⚠️  Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
    
    except Exception as e:
        print(f"❌ Critical error during sync: {e}")
        sys.exit(1)


async def handle_sync_polar_user():
    """Handle the sync-polar-user command."""
    if len(sys.argv) < 3:
        print("❌ Error: sync-polar-user requires a user ID")
        print("Usage: python -m src.commands.management sync-polar-user <user_id>")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[2])
    except ValueError:
        print(f"❌ Error: '{sys.argv[2]}' is not a valid user ID (must be an integer)")
        sys.exit(1)
    
    print(f"🔄 Starting Polar package sync for user {user_id}...")
    
    try:
        success = await sync_single_user_packages(user_id)
        
        if success:
            print(f"✅ Successfully synced user {user_id}")
        else:
            print(f"❌ Failed to sync user {user_id}")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Critical error during sync: {e}")
        sys.exit(1)


def print_help():
    """Print help message."""
    print(__doc__)


def print_env_info():
    """Print environment information for debugging."""
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Polar Environment: {settings.POLAR_ENVIRONMENT}")
    print(f"Polar Access Token: {'✓ Set' if settings.POLAR_ACCESS_TOKEN else '✗ Not Set'}")


if __name__ == "__main__":
    asyncio.run(main())