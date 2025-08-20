import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.api_auth import authenticate_analytics_request, validate_package_match
from src.core.database import get_db
from src.core.rate_limiter import check_rate_limit
from src.core.dependencies import requires_active_subscription_for_api_key
from src.models.analytics_event import AnalyticsEvent
from src.models.api_key import APIKey
from src.schemas.analytics import AnalyticsEventBatch, AnalyticsEventCreate

router = APIRouter(prefix="/api", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.post(
    "/analytics",
    response_model=dict,
    summary="Submit Analytics Event",
    description="Submit a single analytics event for Python package usage tracking.",
    responses={
        200: {
            "description": "Analytics event recorded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "event_id": "123e4567-e89b-12d3-a456-426614174000",
                        "received_at": "2024-01-15T10:30:00Z",
                        "message": "Analytics event recorded successfully",
                    }
                }
            },
        },
        401: {"description": "Invalid API key"},
        400: {"description": "Invalid event data"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error"},
    },
)
async def create_analytics_event(
    request: Request,
    response: Response,
    event_data: AnalyticsEventCreate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(authenticate_analytics_request),
):
    """
    Submit a single analytics event for package usage tracking.

    This endpoint is used by the Klyne Python SDK to automatically send usage analytics
    when your package is imported. API keys are public-facing tracking identifiers,
    similar to Google Analytics tracking IDs.

    ## Authentication
    Requires your public API key via Authorization header:
    ```
    Authorization: Bearer klyne_your_public_api_key_here
    ```

    **Note**: API keys are public identifiers and are safe to include in client-side code,
    similar to Google Analytics tracking IDs. They only allow submitting analytics data
    for your specific package.

    ## Rate Limits
    - 1000 events per hour per API key
    - Rate limit information is returned in response headers

    ## Example Usage

    ### Python SDK (Recommended)
    ```python
    import klyne

    # Initialize in your package's __init__.py
    klyne.init(
        api_key='klyne_your_public_api_key_here',
        project='your-package-name'
    )
    ```

    ### Direct API Call
    ```python
    import requests
    import uuid
    from datetime import datetime

    headers = {"Authorization": "Bearer klyne_your_public_api_key_here"}
    data = {
        "session_id": str(uuid.uuid4()),
        "package_name": "your-package-name",
        "package_version": "1.0.0",
        "python_version": "3.9.7",
        "python_implementation": "CPython",
        "os_type": "Linux",
        "os_version": "Ubuntu 20.04",
        "architecture": "x86_64",
        "event_timestamp": datetime.utcnow().isoformat() + "Z"
    }

    response = requests.post("https://wwww.klyne.dev/api/analytics",
                           headers=headers, json=data)
    print(response.json())
    ```

    ### JavaScript/Node.js
    ```javascript
    const data = {
        session_id: crypto.randomUUID(),
        package_name: "your-package-name",
        package_version: "1.0.0",
        python_version: "3.9.7",
        os_type: "Linux",
        event_timestamp: new Date().toISOString()
    };

    fetch('https://www.klyne.dev/api/analytics', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer klyne_your_public_api_key_here',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    ```
    """

    await requires_active_subscription_for_api_key(api_key, db)
    try:
        # Rate limiting
        await check_rate_limit(
            request=request,
            api_key=api_key.key,
            limit=1000,  # 1000 events per hour per API key
            window_seconds=3600,
        )

        # Validate that API key matches the package in the event
        await validate_package_match(api_key, event_data.package_name)

        # Create analytics event
        analytics_event = AnalyticsEvent(
            api_key=api_key.key,
            session_id=UUID(event_data.session_id),
            package_name=event_data.package_name,
            package_version=event_data.package_version,
            python_version=event_data.python_version,
            python_implementation=event_data.python_implementation,
            os_type=event_data.os_type,
            os_version=event_data.os_version,
            os_release=event_data.os_release,
            architecture=event_data.architecture,
            installation_method=event_data.installation_method,
            virtual_env=event_data.virtual_env,
            virtual_env_type=event_data.virtual_env_type,
            cpu_count=event_data.cpu_count,
            total_memory_gb=event_data.total_memory_gb,
            entry_point=event_data.entry_point,
            extra_data=event_data.extra_data,
            event_timestamp=event_data.event_timestamp,
        )

        db.add(analytics_event)
        await db.commit()
        await db.refresh(analytics_event)

        # Add rate limit headers to response
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])

        logger.info(
            f"Analytics event created for package '{event_data.package_name}' "
            f"version '{event_data.package_version}' "
            f"Python {event_data.python_version} on {event_data.os_type}"
        )

        return {
            "success": True,
            "event_id": str(analytics_event.id),
            "received_at": analytics_event.received_at.isoformat(),
            "message": "Analytics event recorded successfully",
        }

    except HTTPException:
        # Re-raise HTTP exceptions (auth, rate limit, validation errors)
        raise
    except Exception as e:
        logger.error(f"Error creating analytics event: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record analytics event")


@router.post("/analytics/batch", response_model=dict, include_in_schema=False)
async def create_analytics_events_batch(
    request: Request,
    response: Response,
    batch_data: AnalyticsEventBatch,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(authenticate_analytics_request),
):
    """
    Create multiple analytics events in a single request.

    Accepts up to 100 events per batch.
    Requires API key authentication via Authorization header.
    """

    await requires_active_subscription_for_api_key(api_key, db)
    try:
        # Rate limiting - count each event in the batch
        await check_rate_limit(
            request=request,
            api_key=api_key.key,
            limit=1000,  # 1000 events per hour per API key
            window_seconds=3600,
        )

        # Validate batch size
        if len(batch_data.events) > 100:
            raise HTTPException(
                status_code=400, detail="Batch size cannot exceed 100 events"
            )

        if len(batch_data.events) == 0:
            raise HTTPException(status_code=400, detail="Batch cannot be empty")

        created_events = []
        failed_events = []

        for i, event_data in enumerate(batch_data.events):
            try:
                # Validate that API key matches the package in each event
                await validate_package_match(api_key, event_data.package_name)

                # Create analytics event
                analytics_event = AnalyticsEvent(
                    api_key=api_key.key,
                    session_id=UUID(event_data.session_id),
                    package_name=event_data.package_name,
                    package_version=event_data.package_version,
                    python_version=event_data.python_version,
                    python_implementation=event_data.python_implementation,
                    os_type=event_data.os_type,
                    os_version=event_data.os_version,
                    os_release=event_data.os_release,
                    architecture=event_data.architecture,
                    installation_method=event_data.installation_method,
                    virtual_env=event_data.virtual_env,
                    virtual_env_type=event_data.virtual_env_type,
                    cpu_count=event_data.cpu_count,
                    total_memory_gb=event_data.total_memory_gb,
                    entry_point=event_data.entry_point,
                    extra_data=event_data.extra_data,
                    event_timestamp=event_data.event_timestamp,
                )

                db.add(analytics_event)
                created_events.append(
                    {
                        "index": i,
                        "session_id": event_data.session_id,
                        "package_name": event_data.package_name,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to process event {i}: {e}")
                failed_events.append(
                    {
                        "index": i,
                        "error": str(e),
                        "session_id": event_data.session_id
                        if hasattr(event_data, "session_id")
                        else None,
                    }
                )

        # If all events failed, return error
        if len(created_events) == 0:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "All events in batch failed",
                    "failed_events": failed_events,
                },
            )

        # Commit successful events
        await db.commit()

        # Add rate limit headers to response
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])

        logger.info(
            f"Batch analytics: {len(created_events)} events created, "
            f"{len(failed_events)} events failed for package '{api_key.package_name}'"
        )

        return {
            "success": True,
            "created_count": len(created_events),
            "failed_count": len(failed_events),
            "created_events": created_events,
            "failed_events": failed_events if failed_events else None,
            "message": f"Batch processed: {len(created_events)} events created",
        }

    except HTTPException:
        # Re-raise HTTP exceptions (auth, rate limit, validation errors)
        raise
    except Exception as e:
        logger.error(f"Error creating analytics batch: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process analytics batch")


@router.get("/analytics/health", response_model=dict, include_in_schema=False)
async def analytics_health_check():
    """
    Health check endpoint for analytics API.
    No authentication required.
    """
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
