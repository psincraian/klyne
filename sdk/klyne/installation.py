"""
Installation ID management for unique user tracking.

Generates and persists a unique installation ID for each package
to enable pseudonymous tracking across sessions.
"""

import hashlib
import json
import logging
import os
import platform
import stat
import uuid
from pathlib import Path
from typing import Optional, Tuple

_logger = logging.getLogger(__name__)


def get_installation_storage_path(package_name: str) -> Path:
    """
    Get the path to store installation data.

    Uses ~/.klyne/installations/{package_name}.json
    Sets restrictive permissions (0o700) for privacy.
    """
    home_dir = Path.home()
    klyne_dir = home_dir / ".klyne" / "installations"

    # Create directory if it doesn't exist with restrictive permissions
    try:
        klyne_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions: owner read/write/execute only (0o700)
        # This prevents other users on the system from reading installation IDs
        try:
            klyne_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            _logger.debug(f"Set restrictive permissions on {klyne_dir}")
        except (OSError, PermissionError) as e:
            # Permission setting might fail on some filesystems (e.g., FAT32, network drives)
            # Continue anyway - directory was created
            _logger.debug(f"Could not set restrictive permissions on klyne directory: {e}")

    except (OSError, PermissionError) as e:
        _logger.debug(f"Could not create klyne directory at {klyne_dir}: {type(e).__name__}: {e}")
        # Return path anyway, will handle error during read/write

    return klyne_dir / f"{package_name}.json"


def generate_installation_id() -> str:
    """Generate a new random installation UUID."""
    return str(uuid.uuid4())


def calculate_fingerprint_hash(package_name: str) -> str:
    """
    Calculate a hardware/system fingerprint hash for pseudonymous tracking.

    This hash is based on:
    - Package name (to ensure different packages have different fingerprints)
    - OS type and version
    - Architecture
    - Python version
    - CPU count (if available)

    Args:
        package_name: Name of the package (included to ensure per-package uniqueness)

    Returns a SHA256 hash of the fingerprint data.
    """
    try:
        fingerprint_data = {
            "package_name": package_name,  # Include package name for per-package uniqueness
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }

        # Try to add CPU count
        try:
            import multiprocessing
            fingerprint_data["cpu_count"] = multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            pass

        # Create deterministic string representation
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)

        # Generate SHA256 hash
        hash_obj = hashlib.sha256(fingerprint_str.encode("utf-8"))
        return hash_obj.hexdigest()

    except Exception as e:
        _logger.debug(f"Could not calculate fingerprint hash: {e}")
        # Return a package-specific fallback hash
        return hashlib.sha256(f"klyne_fallback_{package_name}".encode("utf-8")).hexdigest()


def load_installation_id(package_name: str) -> Optional[str]:
    """
    Load installation ID from disk for the given package.

    Returns None if file doesn't exist or can't be read.
    """
    storage_path = get_installation_storage_path(package_name)

    try:
        if storage_path.exists():
            with open(storage_path, "r") as f:
                data = json.load(f)
                installation_id = data.get("installation_id")

                if installation_id:
                    _logger.debug(f"Loaded installation ID for {package_name}")
                    return installation_id
    except (OSError, json.JSONDecodeError, PermissionError) as e:
        _logger.debug(f"Could not load installation ID: {e}")

    return None


def save_installation_id(package_name: str, installation_id: str) -> bool:
    """
    Save installation ID to disk for the given package.

    Sets restrictive file permissions (0o600) to prevent other users from reading.
    Returns True if successful, False otherwise.
    """
    storage_path = get_installation_storage_path(package_name)

    try:
        data = {
            "installation_id": installation_id,
            "package_name": package_name,
            "created_at": str(uuid.uuid1().time),
        }

        # Write with restrictive permissions
        # Use os.open with specific flags to create file with restricted permissions
        fd = os.open(
            storage_path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            stat.S_IRUSR | stat.S_IWUSR  # 0o600 - owner read/write only
        )

        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            # If writing fails, close the file descriptor manually
            os.close(fd)
            raise

        _logger.debug(f"Saved installation ID for {package_name} with restrictive permissions")
        return True

    except (OSError, PermissionError) as e:
        _logger.debug(f"Could not save installation ID for {package_name}: {type(e).__name__}: {e}")
        return False


def get_or_create_installation_id(package_name: str) -> Tuple[Optional[str], str]:
    """
    Get existing installation ID or create a new one.

    Returns:
        Tuple of (installation_id, fingerprint_hash)
        - installation_id: UUID string or None if couldn't be created/loaded
        - fingerprint_hash: SHA256 hash of system fingerprint (includes package_name)
    """
    # Always calculate fingerprint hash as fallback (includes package_name for uniqueness)
    fingerprint_hash = calculate_fingerprint_hash(package_name)

    # Try to load existing installation ID
    installation_id = load_installation_id(package_name)

    if installation_id:
        return installation_id, fingerprint_hash

    # Generate new installation ID
    installation_id = generate_installation_id()

    # Try to save it
    if save_installation_id(package_name, installation_id):
        return installation_id, fingerprint_hash
    else:
        # If we can't save, return None and rely on fingerprint
        _logger.debug(f"Using fingerprint-only tracking for {package_name}")
        return None, fingerprint_hash


def get_user_identifier(installation_id: Optional[str], fingerprint_hash: str) -> str:
    """
    Get the user identifier to use for analytics.

    Priority: installation_id > fingerprint_hash
    """
    return installation_id if installation_id else fingerprint_hash
