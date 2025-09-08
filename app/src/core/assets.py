"""
Asset management utilities for resolving Vite build assets.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

# Path to the Vite manifest file
MANIFEST_PATH = Path(__file__).parent.parent / "static" / "dist" / ".vite" / "manifest.json"


@lru_cache(maxsize=1)
def load_manifest() -> Dict:
    """Load the Vite manifest file with caching."""
    try:
        if MANIFEST_PATH.exists():
            with open(MANIFEST_PATH) as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def clear_manifest_cache():
    """Clear the manifest cache - useful in development."""
    load_manifest.cache_clear()


def is_development() -> bool:
    """Check if we're in development mode."""
    return os.getenv("ENVIRONMENT", "development") == "development"


def get_asset_url(entry_name: str) -> Optional[str]:
    """
    Get the built asset URL for a given entry name.
    
    Args:
        entry_name: The entry name from vite.config.js (e.g., 'main', 'dashboard', 'styles')
        
    Returns:
        The built asset URL with hash, or None if not found
    """
    # In development, use Vite dev server
    if is_development():
        # Try common Vite dev server ports
        vite_dev_server = os.getenv("VITE_DEV_SERVER", "http://localhost:3001")
        entry_mappings = {
            'main': 'src/js/main.js',
            'dashboard': 'src/js/dashboard.js',
            'theme-switcher': 'src/js/theme-switcher.js',
        }
        
        input_path = entry_mappings.get(entry_name)
        if input_path:
            return f"{vite_dev_server}/{input_path}"
        return None
    
    # In production, use built assets
    manifest = load_manifest()
    
    # Map entry names to their input paths
    entry_mappings = {
        'main': 'src/js/main.js',
        'dashboard': 'src/js/dashboard.js',
        'theme-switcher': 'src/js/theme-switcher.js',
        'styles': 'src/static/css/input.css'
    }
    
    input_path = entry_mappings.get(entry_name)
    if not input_path or input_path not in manifest:
        return None
        
    entry = manifest[input_path]
    return f"/static/{entry['file']}"


def get_css_url(entry_name: str) -> Optional[str]:
    """
    Get the CSS file URL for a given entry.
    
    Args:
        entry_name: The entry name that has associated CSS
        
    Returns:
        The CSS file URL, or None if not found
    """
    # In development, use Vite dev server for CSS
    if is_development():
        vite_dev_server = os.getenv("VITE_DEV_SERVER", "http://localhost:3001")
        if entry_name == 'styles':
            return f"{vite_dev_server}/src/static/css/input.css"
        return None
    
    # In production, use built assets
    manifest = load_manifest()
    
    entry_mappings = {
        'main': 'src/js/main.js',
        'dashboard': 'src/js/dashboard.js',
        'theme-switcher': 'src/js/theme-switcher.js',
        'styles': 'src/static/css/input.css'
    }
    
    input_path = entry_mappings.get(entry_name)
    if not input_path or input_path not in manifest:
        return None
        
    entry = manifest[input_path]
    
    # For CSS entries, the file itself is the CSS
    if entry_name == 'styles':
        return f"/static/{entry['file']}"
    
    # For JS entries, look for associated CSS
    if 'css' in entry and entry['css']:
        return f"/static/{entry['css'][0]}"
        
    return None


def get_vite_client_url() -> Optional[str]:
    """Get the Vite client script URL for development."""
    if is_development():
        vite_dev_server = os.getenv("VITE_DEV_SERVER", "http://localhost:3001")
        return f"{vite_dev_server}/@vite/client"
    return None