"""
Jinja2 debug utilities for development.
"""
import json
from typing import Any
from jinja2 import Environment
from jinja2.ext import Extension


def debug_filter(value: Any, label: str = "") -> str:
    """
    Debug filter to inspect variables in templates.
    
    Usage in templates:
    {{ variable | debug }}
    {{ variable | debug("custom label") }}
    """
    if label:
        label = f"[{label}] "
    
    if value is None:
        debug_info = f"{label}None"
    elif hasattr(value, '__dict__'):
        # For objects, show type and some attributes
        attrs = []
        for key, val in value.__dict__.items():
            if not key.startswith('_'):
                if isinstance(val, str):
                    attrs.append(f"{key}='{val}'")
                else:
                    attrs.append(f"{key}={type(val).__name__}")
        debug_info = f"{label}{type(value).__name__}({', '.join(attrs)})"
    elif isinstance(value, (dict, list)):
        try:
            debug_info = f"{label}{json.dumps(value, indent=2, default=str)}"
        except (TypeError, ValueError):
            debug_info = f"{label}{type(value).__name__} (non-serializable)"
    else:
        debug_info = f"{label}{repr(value)}"
    
    return f"<!-- DEBUG: {debug_info} -->"


def debug_log_filter(value: Any, label: str = "") -> str:
    """
    Debug filter that also logs to console (server-side).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if label:
        label = f"[{label}] "
    
    logger.info(f"TEMPLATE DEBUG: {label}{repr(value)}")
    return debug_filter(value, label.strip("[] "))


class DebugExtension(Extension):
    """
    Jinja2 extension that adds debug utilities.
    
    Adds global functions:
    - debug(value, label=None): Print debug info about a value
    - vardump(*vars): Dump multiple variables with their names
    """
    
    def __init__(self, environment: Environment):
        super().__init__(environment)
        environment.filters['debug'] = debug_filter
        environment.filters['debug_log'] = debug_log_filter
        environment.globals['debug'] = self.debug_function
        environment.globals['vardump'] = self.vardump_function
    
    def debug_function(self, value: Any, label: str = "") -> str:
        """Global debug function for templates."""
        return debug_filter(value, label)
    
    def vardump_function(self, **kwargs) -> str:
        """Dump multiple variables with their names."""
        output = []
        for name, value in kwargs.items():
            output.append(debug_filter(value, name))
        return "\n".join(output)


def setup_debug_environment(templates: Any) -> None:
    """
    Setup debug utilities for Jinja2 templates.
    
    Args:
        templates: FastAPI Jinja2Templates instance
    """
    # Add the debug extension
    templates.env.add_extension(DebugExtension)
    
    # Add global debug variables
    templates.env.globals['DEBUG'] = True
    templates.env.globals['debug_enabled'] = True