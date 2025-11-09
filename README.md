# Klyne

[![CI/CD](https://github.com/psincraian/klyne/actions/workflows/ci.yml/badge.svg)](https://github.com/psincraian/klyne/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/klyne.svg)](https://badge.fury.io/py/klyne)
[![Python Support](https://img.shields.io/pypi/pyversions/klyne.svg)](https://pypi.org/project/klyne/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Package analytics for Python developers** - Track usage, Python version adoption, OS distribution, and custom events for your Python packages.

[Website](https://klyne.dev) • [Documentation](https://klyne.dev/docs) • [PyPI](https://pypi.org/project/klyne/)

## What is Klyne?

Klyne is a privacy-first analytics platform designed for Python package maintainers. Get insights into how your package is being used without collecting personally identifiable information.

### Key Features

- **Lightweight SDK**: Zero dependencies, minimal overhead
- **Privacy-First**: No PII collection, only aggregated usage metrics
- **Custom Event Tracking**: Track feature usage, errors, and user interactions
- **Rich Insights**: Python versions, OS distribution, environment detection
- **Free Tier**: Get started with no credit card required

## Quick Start

### 1. Install the SDK

```bash
pip install klyne
```

### 2. Get Your API Key

Sign up at [klyne.dev](https://klyne.dev) to get your free API key.

### 3. Integrate in Your Package

```python
import klyne

# Initialize once in your package's __init__.py
klyne.init(
    api_key="klyne_your_api_key_here",
    project="your-package-name",
    package_version="1.0.0"
)
```

That's it! Analytics are automatically collected when users import your package.

### 4. Track Custom Events (Optional)

```python
import klyne

# Track feature usage
klyne.track('feature_used', {
    'feature_name': 'export',
    'file_format': 'csv'
})

# Track errors
klyne.track('error_occurred', {
    'error_type': 'ValidationError',
    'module': 'data_processor'
})
```

## What Gets Tracked?

The SDK automatically collects non-identifying information:

- Python version and implementation (CPython, PyPy, etc.)
- Operating system type, version, and architecture
- Installation context (pip, conda, virtual environment)
- Hardware info (CPU count, memory - rounded for privacy)
- Package name, version, and entry points

**No IP addresses, usernames, file paths, or other PII is collected.**

## Repository Structure

This is a monorepo containing:

- **[`app/`](./app)**: FastAPI web application (landing page, dashboard, analytics API)
- **[`sdk/`](./sdk)**: Python SDK for package analytics
- **[`.github/`](./.github)**: CI/CD pipelines for testing, building, and deployment

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (for PostgreSQL)
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/psincraian/klyne.git
cd klyne

# Start PostgreSQL
docker-compose up -d postgres

# Setup the web app
cd app
uv sync --dev
npm install

# Run development server (with hot reload for CSS + Python)
npm run dev:server
```

The app will be available at `http://localhost:8000`.

### Project Structure

```
klyne/
├── app/                    # FastAPI web application
│   ├── src/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Configuration, auth, dependencies
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── repositories/  # Data access layer
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── services/      # Business logic
│   │   ├── templates/     # Jinja2 templates
│   │   └── static/        # CSS, JS, images
│   ├── tests/             # Test suite
│   ├── alembic/           # Database migrations
│   └── pyproject.toml     # Python dependencies
│
├── sdk/                   # Python SDK
│   ├── klyne/            # SDK source code
│   ├── tests/            # SDK tests
│   └── pyproject.toml    # SDK dependencies
│
└── .github/              # CI/CD workflows
```

### Available Commands

```bash
# From app/ directory

# Development
npm run dev:server      # Run app with hot reload
npm run dev            # Watch CSS changes only
uv run uvicorn src.main:app --reload  # Run Python server only

# Code Quality
uv run ruff check .           # Lint code
uv run ruff check --fix .     # Auto-fix linting issues
uv run ty check .             # Type checking
uv run pytest -v              # Run tests

# Database
uv run alembic revision --autogenerate -m "description"  # Create migration
uv run alembic upgrade head                              # Run migrations

# Frontend
npm run build          # Build production CSS
npm run clean          # Clean generated CSS
```

### SDK Development

```bash
cd sdk

# Install dependencies
uv sync --dev

# Run tests
uv run python test_integration.py

# Lint and type check
uv run ruff check .
uv run ty check .
```

### Testing

The project uses pytest for Python tests:

```bash
cd app
uv run pytest -v                    # Run all tests
uv run pytest tests/test_auth.py    # Run specific test file
uv run pytest -k "test_login"       # Run tests matching pattern
```

## Architecture

### Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy 2.0 (async ORM)
- PostgreSQL 15 (database)
- Alembic (database migrations)
- Pydantic (validation)

**Frontend:**
- Jinja2 (server-side templates)
- Tailwind CSS (styling)
- Modern CSS (custom properties, grid, flexbox)

**Infrastructure:**
- Docker & Docker Compose (local development)
- GitHub Actions (CI/CD)
- GitHub Container Registry (Docker images)
- Coolify (deployment platform)

### Key Patterns

- **Async/Await**: Full async support with SQLAlchemy 2.0
- **Dependency Injection**: FastAPI's dependency system for database sessions
- **Repository Pattern**: Clean separation between data access and business logic
- **Unit of Work**: Transaction management across multiple repositories
- **Server-Side Rendering**: Jinja2 templates with base template inheritance

## Configuration

Copy `.env.example` to `.env` in the `app/` directory and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/klyne

# Security
SECRET_KEY=your-secret-key-here

# Email (Resend)
RESEND_API_KEY=your-resend-api-key

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn

# Subscriptions (Polar.sh - optional)
POLAR_ACCESS_TOKEN=your-polar-token
POLAR_WEBHOOK_SECRET=your-webhook-secret
```

## Deployment

### CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

1. **Test Stage**: Runs tests, linting, and type checking
2. **Build Stage**: Builds Docker image and pushes to GHCR
3. **Deploy Stage**: Triggers Coolify deployment

The pipeline runs on:
- Push to `main` branch
- Pull requests to `main`

### Required Secrets

Configure these in your GitHub repository settings:

- `COOLIFY`: Bearer token for Coolify API deployment

### Manual Deployment

```bash
# Build Docker image
docker build -t klyne:latest ./app

# Run container
docker run -p 8000:8000 --env-file ./app/.env klyne:latest
```

## Code Style & Standards

### Import Organization

```python
# Standard library imports
from datetime import datetime, timezone
from typing import Optional, List
import logging

# Third-party imports
from fastapi import HTTPException

# Local imports
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork
```

### Logging Standards

- Use `logger.info()` for write operations (CREATE, UPDATE, DELETE)
- Use `logger.debug()` for read operations (GET, SELECT, FETCH)
- Use `logger.error()` for exceptions and errors
- Use `logger.warning()` for recoverable issues

```python
logger = logging.getLogger(__name__)

logger.info(f"Creating new user with email {user_data.email}")
logger.debug(f"Fetching user by email {email}")
```

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`uv run pytest -v && uv run ruff check .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [klyne.dev/docs](https://klyne.dev/docs)
- **Issues**: [GitHub Issues](https://github.com/psincraian/klyne/issues)
- **Email**: hello@klyne.dev

## Acknowledgments

Built with modern tools:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [uv](https://docs.astral.sh/uv/) - Package management
- [Coolify](https://coolify.io/) - Deployment platform

---

**[Get started with Klyne today →](https://klyne.dev)**
