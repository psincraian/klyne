"""
Data collection utilities for gathering system and environment metrics.
Uses only standard library modules to minimize dependencies.
"""

import os
import sys
import platform
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def get_python_info() -> Dict[str, str]:
    """Get Python version and implementation info."""
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_implementation": platform.python_implementation(),
    }


def get_system_info() -> Dict[str, str]:
    """Get operating system and hardware info."""
    info = {
        "os_type": platform.system(),
        "architecture": platform.machine(),
    }
    
    # Add OS version info safely
    try:
        info["os_version"] = platform.release()
    except Exception:
        pass
    
    # Add OS release info (more descriptive)
    try:
        if platform.system() == "Linux":
            # Try to get Linux distribution info
            try:
                import distro
                info["os_release"] = f"{distro.name()} {distro.version()}"
            except ImportError:
                # Fallback for systems without distro package
                try:
                    with open("/etc/os-release", "r") as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.startswith("PRETTY_NAME="):
                                info["os_release"] = line.split("=", 1)[1].strip().strip('"')
                                break
                except Exception:
                    pass
        elif platform.system() == "Windows":
            info["os_release"] = f"Windows {platform.release()}"
        elif platform.system() == "Darwin":
            info["os_release"] = f"macOS {platform.release()}"
    except Exception:
        pass
    
    return info


def get_environment_info() -> Dict[str, Any]:
    """Get Python environment information."""
    info = {}
    
    # Detect virtual environment
    try:
        # Check for various virtual environment indicators
        virtual_env = False
        virtual_env_type = None
        
        if hasattr(sys, 'real_prefix'):
            # virtualenv
            virtual_env = True
            virtual_env_type = "virtualenv"
        elif hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            # venv or conda
            virtual_env = True
            if "conda" in sys.prefix or "anaconda" in sys.prefix or "miniconda" in sys.prefix:
                virtual_env_type = "conda"
            else:
                virtual_env_type = "venv"
        elif os.environ.get('VIRTUAL_ENV'):
            virtual_env = True
            virtual_env_type = "unknown"
        elif os.environ.get('CONDA_DEFAULT_ENV'):
            virtual_env = True
            virtual_env_type = "conda"
        
        info["virtual_env"] = virtual_env
        if virtual_env_type:
            info["virtual_env_type"] = virtual_env_type
            
    except Exception:
        info["virtual_env"] = False
    
    # Try to detect installation method
    try:
        # This is a heuristic - not 100% accurate but good enough
        installation_method = None
        
        if os.environ.get('CONDA_DEFAULT_ENV'):
            installation_method = "conda"
        elif hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # In virtual environment, likely pip
            installation_method = "pip"
        else:
            # System installation, assume pip
            installation_method = "pip"
        
        if installation_method:
            info["installation_method"] = installation_method
            
    except Exception:
        pass
    
    return info


def get_hardware_info() -> Dict[str, Any]:
    """Get basic hardware information (optional, privacy-conscious)."""
    info = {}
    
    # CPU count
    try:
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass
    
    # Memory information (rounded to GB for privacy)
    try:
        import psutil
        memory = psutil.virtual_memory()
        info["total_memory_gb"] = round(memory.total / (1024**3))
    except ImportError:
        # psutil not available, try alternative methods
        try:
            if platform.system() == "Linux":
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            # Convert KB to GB
                            memory_kb = int(line.split()[1])
                            info["total_memory_gb"] = round(memory_kb / (1024**2))
                            break
        except Exception:
            pass
    except Exception:
        pass
    
    return info


def create_analytics_event(
    api_key: str,
    package_name: str,
    package_version: str,
    session_id: Optional[str] = None,
    entry_point: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    installation_id: Optional[str] = None,
    fingerprint_hash: Optional[str] = None,
    user_identifier: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a complete analytics event with system information.

    Args:
        api_key: Klyne API key
        package_name: Name of the package
        package_version: Version of the package
        session_id: Optional session ID (generates UUID if not provided)
        entry_point: Optional entry point/function name
        extra_data: Optional additional data
        installation_id: Optional installation UUID for unique user tracking
        fingerprint_hash: Optional hardware fingerprint hash
        user_identifier: Optional user identifier (installation_id or fingerprint_hash)

    Returns:
        Complete analytics event dictionary
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Collect system information
    event = {
        "api_key": api_key,
        "session_id": session_id,
        "package_name": package_name,
        "package_version": package_version,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Add unique user tracking fields
    if installation_id:
        event["installation_id"] = installation_id
    if fingerprint_hash:
        event["fingerprint_hash"] = fingerprint_hash
    if user_identifier:
        event["user_identifier"] = user_identifier

    # Add Python info
    event.update(get_python_info())

    # Add system info
    event.update(get_system_info())

    # Add environment info
    event.update(get_environment_info())

    # Add hardware info (optional)
    hardware_info = get_hardware_info()
    if hardware_info:
        event.update(hardware_info)

    # Add optional fields
    if entry_point:
        event["entry_point"] = entry_point

    if extra_data:
        event["extra_data"] = extra_data

    return event


def create_session_id() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())