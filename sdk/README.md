# Klyne Python SDK

[![PyPI version](https://badge.fury.io/py/klyne.svg)](https://badge.fury.io/py/klyne)
[![Python Support](https://img.shields.io/pypi/pyversions/klyne.svg)](https://pypi.org/project/klyne/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Lightweight Python package analytics SDK for [Klyne](https://klyne.dev). Track package usage, Python version adoption, OS distribution, and more with minimal overhead.

## Features

- =� **Lightweight**: Zero dependencies, uses only Python standard library
- � **Non-blocking**: Asynchronous data transmission in background threads
- = **Privacy-first**: No PII collection, only aggregated usage metrics
- =� **Robust**: Graceful error handling and automatic retries
- =� **Rich insights**: Python versions, OS distribution, environment detection
- <� **Simple API**: One-line integration with sensible defaults

## Installation

```bash
pip install klyne
```

## Quick Start

```python
import klyne

# Initialize once in your package
klyne.init(
    api_key="klyne_your_api_key_here",
    project="your-package-name",
    package_version="1.0.0"
)

# That's it! Analytics are automatically collected
```

## What Gets Tracked

The SDK automatically collects:

- **Python Environment**: Version, implementation (CPython/PyPy)
- **Operating System**: Type, version, architecture
- **Installation Context**: pip/conda, virtual environment detection
- **Hardware**: CPU count, memory (rounded for privacy)
- **Package Info**: Name, version, entry points used

**No personally identifiable information is collected.**

## Advanced Usage

### Custom Event Tracking

```python
import klyne

# Track specific functions or features
klyne.track_event(
    entry_point="advanced_feature",
    extra_data={"mode": "premium", "user_type": "enterprise"}
)
```

### Configuration Options

```python
import klyne

klyne.init(
    api_key="klyne_your_api_key_here",
    project="your-package-name", 
    package_version="1.0.0",
    base_url="https://api.klyne.dev",  # Default API URL
    enabled=True,                      # Enable/disable analytics
    debug=False                        # Debug logging
)
```

### Environment-based Control

```python
import os
import klyne

# Disable in development
enabled = os.getenv("ENVIRONMENT") == "production"

klyne.init(
    api_key=os.getenv("KLYNE_API_KEY"),
    project="your-package-name",
    enabled=enabled
)
```

### Manual Control

```python
import klyne

# Disable analytics
klyne.disable()

# Re-enable analytics
klyne.enable()

# Check status
if klyne.is_enabled():
    print("Analytics are active")

# Flush pending events (useful for short-lived scripts)
klyne.flush(timeout=5.0)
```

## Requirements

- Python 3.7+
- No external dependencies
- Internet connection (for sending analytics)

## License

MIT License

---

**[Get your free API key at klyne.dev](https://klyne.dev)**