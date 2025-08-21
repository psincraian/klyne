# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Klyne is a package analytics tool for Python packages (similar to Google Analytics but for package usage). This is a monorepo containing:

- **`app/`**: FastAPI web application (landing page with email collection)
- **`sdk/`**: Python SDK for package analytics (early stage/placeholder)

The current implementation is a pre-launch landing page to capture early access signups.

## Development Commands

### Setup and Running
```bash
# Start PostgreSQL database
docker-compose up -d postgres

# Install dependencies (from app/ directory)
cd app && uv sync && npm install

# Run development server with hot reload (CSS + Python)
npm run dev:server

# OR run components separately:
# Terminal 1: CSS hot reload
npm run dev

# Terminal 2: Python server
uv run uvicorn src.main:app --reload
```

### Package Management
- Use **UV** for Python package management: `uv add <package>`
- Use **npm** for frontend dependencies: `npm install <package>`
- Dependencies are defined in `pyproject.toml` and `package.json` files
- Lock files (`uv.lock` and `package-lock.json`) ensure reproducible builds

### Frontend Development
```bash
# Build CSS for production
npm run build

# Watch CSS changes during development
npm run dev

# Clean generated CSS
npm run clean
```

### Linting and Code Quality
```bash
# Run linting (from app/ directory)
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

## Architecture

### FastAPI Application Structure (app/src/)

**Core Infrastructure:**
- `main.py`: FastAPI app with async lifespan management and template routing
- `core/config.py`: Pydantic settings with environment variable support
- `core/database.py`: SQLAlchemy async engine with session management

**Data Layer:**
- `models/`: SQLAlchemy ORM models with async support
- `schemas/`: Pydantic schemas for validation (using EmailStr for email validation)
- Current model: `EmailSignup` for collecting email addresses

**Presentation Layer:**
- `templates/`: Jinja2 templates with base template inheritance
- `static/css/`: Modern CSS with custom properties and responsive design
- Template structure: base.html → index.html (landing) + success.html (post-signup)

**Key Patterns:**
- Full async/await with SQLAlchemy 2.0
- Dependency injection for database sessions
- Server-side rendering with Jinja2
- Environment-based configuration

### Database Setup

- **PostgreSQL 15** via Docker Compose
- **Async SQLAlchemy** with asyncpg driver
- **Connection**: `postgresql+asyncpg://postgres:postgres@localhost/klyne`
- **Migrations**: Alembic configured (migration files not yet created)

## Configuration

### Environment Variables
- Copy `.env.example` to `.env` for local development
- Database URL configurable via `DATABASE_URL`
- Settings managed through Pydantic Settings in `core/config.py`

### Required Dependencies
The app requires these key dependencies:
- `fastapi`, `uvicorn` (web framework)
- `sqlalchemy`, `asyncpg`, `greenlet` (async database)
- `jinja2` (templating)
- `pydantic`, `pydantic-settings`, `email-validator` (validation)
- `alembic` (migrations)
- `ruff` (linting - dev dependency)

## Development Patterns

### Adding New Features
- **Database models**: Add to `src/models/` following existing async patterns
- **API endpoints**: Place in `src/api/` with proper dependency injection
- **Templates**: Extend base template in `src/templates/`
- **Validation**: Create Pydantic schemas in `src/schemas/`

### Code Style and Standards

**Import Organization:**
- Standard library imports first
- Third-party library imports second  
- Local/project imports last
- Each group separated by a blank line
- Sort imports alphabetically within each group
- Example:
```python
from datetime import datetime, timezone
from typing import Optional, List
import logging

from fastapi import HTTPException

from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork
```

**Logging Standards:**
- Use `logger.info()` for write operations (CREATE, UPDATE, DELETE, POST, PUT, PATCH operations)
- Use `logger.debug()` for read operations (GET, SELECT, FETCH, LIST operations)
- Use `logger.error()` for exceptions and error conditions
- Use `logger.warning()` for recoverable issues or deprecated usage
- Always use module-level loggers: `logger = logging.getLogger(__name__)`
- Examples:
```python
# Write operations - use info
logger.info(f"Creating new user with email {user_data.email}")
logger.info(f"Updated API key {api_key.id} for user {user_id}")

# Read operations - use debug  
logger.debug(f"Fetching user by email {email}")
logger.debug(f"Found {len(results)} analytics events")
```

### Database Work
- Models use SQLAlchemy 2.0 declarative base
- All database operations are async
- Use `Depends(get_db)` for session injection
- Database tables created automatically via lifespan event

### Frontend Development
- Templates use Jinja2 with block inheritance
- CSS uses modern features (custom properties, grid, flexbox)
- Responsive design with mobile-first approach
- Static files served from `src/static/`

## Business Context

Klyne aims to provide analytics for Python packages including:
- OS distribution tracking
- Python version adoption
- Active usage patterns

The integration pattern will be: `klyne.init(api_key='XX', project='pandas')`

## Deployment

### CI/CD Pipeline
- **GitHub Actions**: `.github/workflows/ci.yml`
- **Triggers**: Push to main branch or manual workflow dispatch
- **Process**: Tests → Linting → Docker build → Push to GHCR → Deploy to Coolify

### Production Deployment
- **Platform**: Coolify (self-hosted PaaS)
- **Container Registry**: GitHub Container Registry (`ghcr.io/petru/klyne:latest`)
- **Deployment**: Automatic via Coolify API call from GitHub Actions

### Required Secrets
Add these secrets to your GitHub repository (Settings → Secrets):
- `COOLIFY`: Bearer token for Coolify API deployment trigger