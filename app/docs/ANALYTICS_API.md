# Klyne Analytics API

The Klyne Analytics API allows you to submit package usage analytics data for tracking and analysis.

## Authentication

All analytics endpoints require API key authentication via the `Authorization` header:

```
Authorization: Bearer klyne_your_api_key_here
```

## Endpoints

### Health Check

```http
GET /api/analytics/health
```

No authentication required. Returns service status.

**Response:**
```json
{
  "status": "healthy",
  "service": "analytics",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Submit Single Analytics Event

```http
POST /api/analytics
```

Submit a single analytics event for package usage tracking.

**Headers:**
```
Authorization: Bearer klyne_your_api_key_here
Content-Type: application/json
```

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "package_name": "your-package",
  "package_version": "1.0.0",
  "python_version": "3.11.5",
  "python_implementation": "CPython",
  "os_type": "Linux",
  "os_version": "5.15.0",
  "os_release": "Ubuntu 22.04",
  "architecture": "x86_64",
  "installation_method": "pip",
  "virtual_env": true,
  "virtual_env_type": "venv",
  "cpu_count": 8,
  "total_memory_gb": 16,
  "entry_point": "your_package.main",
  "event_timestamp": "2024-01-15T10:30:00Z",
  "extra_data": {
    "custom_field": "value"
  }
}
```

**Required Fields:**
- `session_id`: Unique UUID for this package run
- `package_name`: Name of your package (must match API key)
- `package_version`: Version of your package
- `python_version`: Python version (e.g., "3.11.5")
- `os_type`: Operating system type (Linux, Windows, Darwin, etc.)
- `event_timestamp`: ISO timestamp when event occurred

**Response:**
```json
{
  "success": true,
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "received_at": "2024-01-15T10:30:01Z",
  "message": "Analytics event recorded successfully"
}
```

### Submit Batch Analytics Events

```http
POST /api/analytics/batch
```

Submit multiple analytics events in a single request (up to 100 events).

**Headers:**
```
Authorization: Bearer klyne_your_api_key_here
Content-Type: application/json
```

**Request Body:**
```json
{
  "events": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "package_name": "your-package",
      "package_version": "1.0.0",
      "python_version": "3.11.5",
      "os_type": "Linux",
      "event_timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440001",
      "package_name": "your-package",
      "package_version": "1.0.0",
      "python_version": "3.10.0",
      "os_type": "Windows",
      "event_timestamp": "2024-01-15T10:31:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "created_count": 2,
  "failed_count": 0,
  "created_events": [
    {
      "index": 0,
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "package_name": "your-package"
    },
    {
      "index": 1,
      "session_id": "550e8400-e29b-41d4-a716-446655440001",
      "package_name": "your-package"
    }
  ],
  "failed_events": null,
  "message": "Batch processed: 2 events created"
}
```

## Rate Limiting

- **Limit**: 1000 events per hour per API key
- **Headers**: Rate limit information is included in response headers:
  - `X-RateLimit-Limit`: Maximum requests per hour
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

If rate limit is exceeded, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": "Rate limit exceeded",
  "limit": 1000,
  "window_seconds": 3600,
  "reset_time": "2024-01-15T11:30:00Z",
  "current_usage": 1001
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "API key required. Include 'Authorization: Bearer <api_key>' header."
}
```

### 403 Forbidden
```json
{
  "detail": "API key is not authorized for package 'other-package'. This key is for package 'your-package'"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["python_version"],
      "msg": "Invalid Python version format",
      "type": "value_error"
    }
  ]
}
```

### 429 Rate Limit Exceeded
See rate limiting section above.

## Python SDK Integration Example

```python
import klyne
import uuid
from datetime import datetime, timezone

# Initialize Klyne (this should be done once in your package)
klyne.init(
    api_key="klyne_your_api_key_here",
    package_name="your-package",
    package_version="1.0.0"
)

# Event will be automatically sent when package is imported/used
# You can also manually track specific events:
klyne.track_event(
    session_id=str(uuid.uuid4()),
    entry_point="your_package.special_function",
    extra_data={"feature_used": "advanced_mode"}
)
```

## Best Practices

1. **Unique Session IDs**: Generate a new UUID for each package run/session
2. **Batch Requests**: Use the batch endpoint for better performance when submitting multiple events
3. **Error Handling**: Always handle rate limiting and authentication errors gracefully
4. **Privacy**: No personally identifiable information should be included in events
5. **Minimal Data**: Only collect the analytics data you actually need

## Data Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | UUID string | Yes | Unique identifier for this package run |
| `package_name` | string | Yes | Package name (must match API key) |
| `package_version` | string | Yes | Package version |
| `python_version` | string | Yes | Python version (e.g., "3.11.5") |
| `python_implementation` | string | No | Python implementation (CPython, PyPy, etc.) |
| `os_type` | string | Yes | Operating system (Linux, Windows, Darwin, etc.) |
| `os_version` | string | No | OS version |
| `os_release` | string | No | OS release name |
| `architecture` | string | No | CPU architecture (x86_64, arm64, etc.) |
| `installation_method` | string | No | How package was installed (pip, conda, etc.) |
| `virtual_env` | boolean | No | Whether running in virtual environment |
| `virtual_env_type` | string | No | Type of virtual environment |
| `cpu_count` | integer | No | Number of CPU cores |
| `total_memory_gb` | integer | No | Total memory in GB |
| `entry_point` | string | No | Entry point or function used |
| `event_timestamp` | ISO datetime | Yes | When the event occurred |
| `extra_data` | object | No | Additional custom data |