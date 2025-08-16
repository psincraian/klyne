"""
Shared template configuration for the application.
"""
from fastapi.templating import Jinja2Templates
from src.core.assets import get_asset_url, get_css_url, get_vite_client_url
from src.utils.jinja_debug import setup_debug_environment


def create_templates_instance() -> Jinja2Templates:
    """Create a configured Jinja2Templates instance with asset management functions."""
    templates = Jinja2Templates(directory="src/templates", autoescape=True)
    
    # Add asset management functions to template context
    templates.env.globals['get_asset_url'] = get_asset_url
    templates.env.globals['get_css_url'] = get_css_url
    templates.env.globals['get_vite_client_url'] = get_vite_client_url
    
    # Setup debug utilities for development
    setup_debug_environment(templates)
    
    return templates


# Global templates instance
templates = create_templates_instance()