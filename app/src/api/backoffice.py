from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from src.core.database import get_db
from src.core.auth import require_admin
from src.models.user import User
from src.models.api_key import APIKey
from src.models.analytics_event import AnalyticsEvent

router = APIRouter(prefix="/backoffice", tags=["backoffice"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/", response_class=HTMLResponse)
async def backoffice_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user_id: int = Depends(require_admin)
):
    """Admin dashboard with overview statistics."""
    
    # Get basic statistics
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True, User.is_verified == True)
    )
    total_api_keys = await db.scalar(select(func.count(APIKey.id)))
    unique_packages = await db.scalar(select(func.count(func.distinct(APIKey.package_name))))
    total_events = await db.scalar(select(func.count(AnalyticsEvent.id)))
    
    # Get week statistics
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_users_this_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    new_keys_this_week = await db.scalar(
        select(func.count(APIKey.id)).where(APIKey.created_at >= week_ago)
    )
    new_events_this_week = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.received_at >= week_ago)
    )
    
    # Get recent users (last 5)
    recent_users_result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(5)
    )
    recent_users = recent_users_result.scalars().all()
    
    # Get recent API keys (last 5) with user information
    recent_keys_result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user))
        .order_by(APIKey.created_at.desc())
        .limit(5)
    )
    recent_api_keys = recent_keys_result.scalars().all()
    
    stats = {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "total_api_keys": total_api_keys or 0,
        "unique_packages": unique_packages or 0,
        "total_events": total_events or 0,
        "new_users_this_week": new_users_this_week or 0,
        "new_keys_this_week": new_keys_this_week or 0,
        "new_events_this_week": new_events_this_week or 0,
    }
    
    return templates.TemplateResponse(
        "backoffice/dashboard.html",
        {
            "request": request,
            "stats": stats,
            "recent_users": recent_users,
            "recent_api_keys": recent_api_keys,
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def backoffice_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user_id: int = Depends(require_admin)
):
    """List all users with statistics."""
    
    # Get user statistics
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True, User.is_verified == True)
    )
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    admin_users = await db.scalar(
        select(func.count(User.id)).where(User.is_admin == True)
    )
    
    # Get all users with their API key counts
    users_result = await db.execute(
        select(
            User,
            func.count(APIKey.id).label('api_key_count')
        )
        .outerjoin(APIKey)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    
    users_with_counts = []
    for user, api_key_count in users_result:
        user.api_key_count = api_key_count
        users_with_counts.append(user)
    
    return templates.TemplateResponse(
        "backoffice/users.html",
        {
            "request": request,
            "users": users_with_counts,
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "verified_users": verified_users or 0,
            "admin_users": admin_users or 0,
        }
    )


@router.get("/api-keys", response_class=HTMLResponse)
async def backoffice_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user_id: int = Depends(require_admin)
):
    """List all API keys with statistics."""
    
    # Get API key statistics
    total_keys = await db.scalar(select(func.count(APIKey.id)))
    unique_packages = await db.scalar(select(func.count(func.distinct(APIKey.package_name))))
    
    # Get time-based statistics
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    keys_this_month = await db.scalar(
        select(func.count(APIKey.id)).where(APIKey.created_at >= month_ago)
    )
    keys_this_week = await db.scalar(
        select(func.count(APIKey.id)).where(APIKey.created_at >= week_ago)
    )
    
    # Get all API keys with user information (eager load the user relationship)
    api_keys_result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user))
        .order_by(APIKey.created_at.desc())
    )
    api_keys = api_keys_result.scalars().all()
    
    return templates.TemplateResponse(
        "backoffice/api-keys.html",
        {
            "request": request,
            "api_keys": api_keys,
            "total_keys": total_keys or 0,
            "unique_packages": unique_packages or 0,
            "keys_this_month": keys_this_month or 0,
            "keys_this_week": keys_this_week or 0,
        }
    )


@router.get("/events", response_class=HTMLResponse)
async def backoffice_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user_id: int = Depends(require_admin)
):
    """List all analytics events with statistics."""
    
    # Get event statistics
    total_events = await db.scalar(select(func.count(AnalyticsEvent.id)))
    processed_events = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.processed == True)
    )
    pending_events = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.processed == False)
    )
    
    # Get time-based statistics
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    events_today = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.received_at >= today)
    )
    events_this_week = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.received_at >= week_ago)
    )
    events_this_month = await db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.received_at >= month_ago)
    )
    
    # Get unique packages from events
    unique_packages_from_events = await db.scalar(
        select(func.count(func.distinct(AnalyticsEvent.package_name)))
    )
    
    # Get all events with pagination (limit to last 100 for performance)
    events_result = await db.execute(
        select(AnalyticsEvent)
        .order_by(AnalyticsEvent.received_at.desc())
        .limit(100)
    )
    events = events_result.scalars().all()
    
    return templates.TemplateResponse(
        "backoffice/events.html",
        {
            "request": request,
            "events": events,
            "total_events": total_events or 0,
            "processed_events": processed_events or 0,
            "pending_events": pending_events or 0,
            "events_today": events_today or 0,
            "events_this_week": events_this_week or 0,
            "events_this_month": events_this_month or 0,
            "unique_packages_from_events": unique_packages_from_events or 0,
        }
    )