# Klyne - Package Analytics Platform

**ALWAYS follow these instructions first and fallback to search or exploration only when the information here is incomplete or found to be in error.**

Klyne is a package analytics tool for Python packages (similar to Google Analytics but for package usage). This is a monorepo containing:

- **`app/`**: FastAPI web application (landing page with user authentication and analytics dashboard)  
- **`sdk/`**: Python SDK for package analytics (zero dependencies, production-ready)

## Critical Setup Requirements

### Prerequisites and Installation
Install these tools in exact order with verified commands:

```bash
# Install uv (Python package manager) - REQUIRED
pip install uv

# Install Node.js 20+ (if not available)
# Use system package manager or download from nodejs.org

# Verify installations
uv --version  # Should show 0.8+ 
node --version  # Should show v20+
npm --version   # Should show 10+
```

### Database Setup
```bash
# Start PostgreSQL database - REQUIRED for all development
docker compose up -d postgres

# Wait for database health check (typically 10-15 seconds)
# Database runs on port 5433 (not default 5432)
# Connection: postgresql+asyncpg://postgres:postgres@localhost:5433/klyne
```

### App Development Environment
```bash
# Navigate to app directory - ALL app commands run from here
cd app

# Copy environment file and configure
cp .env.example .env

# Install dependencies - NEVER CANCEL: Takes 45+ seconds
# Set timeout to 90+ seconds minimum
uv sync && npm install

# Build frontend assets - NEVER CANCEL: Takes 15+ seconds  
# Set timeout to 30+ seconds minimum
npm run build
```

## Development Commands

### Running the Application
```bash
# From app/ directory - PREFERRED method for development
# Runs both CSS hot reload and Python server with auto-reload
npm run dev:server
# Accessible at http://localhost:8000 (FastAPI)
# CSS dev server at http://localhost:3001 (Vite)

# OR run components separately:
# Terminal 1: CSS hot reload
npm run dev

# Terminal 2: Python server  
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing and Validation

**CRITICAL TIMEOUTS - NEVER CANCEL these operations:**

```bash
# Run tests - NEVER CANCEL: Takes 23+ seconds
# Set timeout to 45+ seconds minimum
uv run pytest -v

# Run linting - Fast operation (<1 second)
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Build frontend for production - NEVER CANCEL: Takes 15+ seconds
# Set timeout to 30+ seconds minimum  
npm run build
```

### SDK Development
```bash
# Navigate to SDK directory
cd sdk

# Install SDK dependencies - Fast operation (~1 second)
uv sync

# Run integration tests - NEVER CANCEL: Takes 6+ seconds
# Set timeout to 15+ seconds minimum
uv run python test_integration.py
```

## Validation Scenarios

**ALWAYS test these complete user workflows after making changes:**

### Basic Application Health
```bash
# From app/ directory with server running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
# Should return: 200

# Test homepage loads
curl -s http://localhost:8000/ | grep -q "Klyne - Package Analytics"
# Should succeed (exit code 0)

# Test registration page 
curl -s http://localhost:8000/register | grep -q "Register"
# Should succeed (exit code 0)
```

### Development Server Validation
1. **Start the combined development server**: `npm run dev:server`
2. **Verify both services start** (typically takes 5-10 seconds):
   - CSS dev server: http://localhost:3001
   - FastAPI server: http://localhost:8000  
3. **Test hot reload**: Make a small change to a CSS file and verify reload
4. **Test API endpoints**: Visit /register, /login pages to ensure they load

### SDK Integration Validation
```bash
# From sdk/ directory
uv run python test_integration.py
# Should show: "✅ All integration tests passed!"
# Network errors for hostname resolution are expected and handled gracefully
```

## Common Issues and Solutions

### Logfire Authentication Error
**Problem**: `LogfireConfigError: You are not logged into Logfire`
**Solution**: Logfire is conditionally configured. Set fake token in .env:
```bash
echo "LOGFIRE_TOKEN=fake-token-for-testing" >> .env
```

### Database Connection Issues  
**Problem**: Database connection failures
**Solution**: Ensure PostgreSQL is running and healthy:
```bash
docker compose ps postgres  # Should show "Up" status
docker compose logs postgres  # Check for errors
```

### Build Failures
**Problem**: Frontend build fails
**Solution**: Clean and reinstall dependencies:
```bash
npm run clean
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Test Failures
**Known Issue**: Some tests fail due to authentication/database state (18 failures expected)
**Impact**: This is a known issue and does not affect development
**Action**: Focus only on new test failures introduced by your changes

## Repository Structure

### Key Application Files
- `app/src/main.py`: FastAPI application entry point
- `app/src/core/config.py`: Environment configuration and settings
- `app/src/core/database.py`: Database connection and session management
- `app/src/models/`: SQLAlchemy ORM models (async)
- `app/src/templates/`: Jinja2 templates with base inheritance
- `app/src/static/`: Static assets (CSS built by Vite, fonts, images)

### Key Configuration Files
- `app/pyproject.toml`: Python dependencies and build config
- `app/package.json`: Node.js dependencies and scripts
- `app/.env`: Environment variables (copy from .env.example)
- `docker-compose.yml`: PostgreSQL database configuration

### Build System
- **Python**: UV package manager with virtual environments
- **Frontend**: Vite + TailwindCSS + DaisyUI for styling
- **Database**: PostgreSQL 15 with async SQLAlchemy 2.0
- **Templates**: Jinja2 with block inheritance pattern

## Development Patterns

### Code Style Requirements
**Import Organization** (enforced by ruff):
```python
# Standard library imports first
from datetime import datetime, timezone
from typing import Optional, List
import logging

# Third-party library imports second  
from fastapi import HTTPException

# Local/project imports last
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork
```

**Logging Standards**:
- Use `logger.info()` for write operations (CREATE, UPDATE, DELETE)
- Use `logger.debug()` for read operations (GET, SELECT, FETCH)
- Use `logger.error()` for exceptions and error conditions
- Always use module-level loggers: `logger = logging.getLogger(__name__)`

### Database Patterns
- All database operations are async using SQLAlchemy 2.0
- Use `Depends(get_db)` for session injection in FastAPI endpoints
- Models use declarative base with async patterns
- Database tables are created automatically via lifespan events

### Frontend Development
- Templates extend base template: `{% extends "base.html" %}`
- CSS uses TailwindCSS + DaisyUI component framework
- Static files served from `src/static/dist/` (built by Vite)
- Responsive design with mobile-first approach

## Continuous Integration

### GitHub Actions Workflow
- **Triggers**: Push to main branch or PR creation
- **Process**: Tests → Linting → Docker build → Deploy
- **Services**: PostgreSQL test database, Node.js 20, Python 3.11
- **Deployment**: Automatic to Coolify platform via container registry

### Pre-commit Validation
**ALWAYS run before committing**:
```bash
# From app/ directory
uv run ruff check --fix .  # Fix linting issues
uv run pytest -v          # Run tests (some failures expected)
npm run build             # Verify frontend builds
```

## Performance Expectations

### Build and Test Timings
- **Database startup**: ~10 seconds via Docker Compose
- **Dependency installation**: ~45 seconds (uv sync + npm install)
- **Frontend build**: ~15 seconds (npm run build) 
- **Test suite**: ~23 seconds (pytest with 18 expected failures)
- **Linting**: <1 second (ruff check)
- **SDK tests**: ~6 seconds (integration test suite)
- **Server startup**: ~5 seconds (development mode)

### Timeout Recommendations
**CRITICAL - NEVER CANCEL these operations before timeouts:**
- Dependency installation: Set 90+ second timeout
- Frontend builds: Set 30+ second timeout  
- Test execution: Set 45+ second timeout
- SDK tests: Set 15+ second timeout

## Troubleshooting

### When Commands Fail
1. **Check prerequisites**: Ensure uv, Node.js 20+, Docker are installed
2. **Verify database**: `docker compose ps` should show postgres running
3. **Clean state**: Remove .venv, node_modules, rebuild from scratch
4. **Check logs**: Server logs show detailed error information
5. **Environment file**: Ensure .env exists with required variables

### Common Command Sequences
**Fresh setup**:
```bash
docker compose up -d postgres
cd app
cp .env.example .env
uv sync && npm install
npm run build
npm run dev:server
```

**After changes**:
```bash
uv run ruff check --fix .
uv run pytest -v
npm run build
```

**Clean restart**:
```bash
docker compose down
docker compose up -d postgres
cd app
npm run clean
rm -rf .venv node_modules
uv sync && npm install
npm run build
```

This file contains all essential information for working with Klyne. Refer to CLAUDE.md for additional architectural details and business context.