"""
APScheduler integration for Klyne application.
Manages scheduled tasks including daily Polar package sync.
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from src.core.config import settings
from src.commands.sync_polar_packages import sync_all_users_packages
from src.commands.cleanup_free_plan_data import cleanup_free_plan_analytics_data

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.
    
    Returns:
        Configured AsyncIOScheduler instance
    """
    jobstores = {
        'default': MemoryJobStore()
    }
    
    executors = {
        'default': AsyncIOExecutor()
    }
    
    job_defaults = {
        'coalesce': True,  # Combine multiple pending jobs into one
        'max_instances': 1,  # Only allow one instance of each job
        'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
    }
    
    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    return scheduler


async def setup_scheduler() -> AsyncIOScheduler:
    """
    Set up and configure the scheduler with all jobs.
    
    Returns:
        Started scheduler instance
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already exists, shutting down existing one")
        await shutdown_scheduler()
    
    scheduler = create_scheduler()
    
    # Add scheduled jobs if sync is enabled
    if settings.POLAR_SYNC_ENABLED:
        logger.info(
            f"Scheduling daily Polar sync at {settings.POLAR_SYNC_HOUR:02d}:"
            f"{settings.POLAR_SYNC_MINUTE:02d} UTC"
        )
        
        scheduler.add_job(
            sync_all_users_packages,
            trigger='cron',
            hour=settings.POLAR_SYNC_HOUR,
            minute=settings.POLAR_SYNC_MINUTE,
            id='polar_daily_sync',
            name='Daily Polar Package Sync',
            replace_existing=True
        )
    else:
        logger.info("Polar sync is disabled, skipping job scheduling")
    
    # Add data cleanup job for free plan users
    logger.info(
        f"Scheduling daily free plan data cleanup at {settings.DATA_CLEANUP_HOUR:02d}:"
        f"{settings.DATA_CLEANUP_MINUTE:02d} UTC (retention: {settings.FREE_PLAN_DATA_RETENTION_DAYS} days)"
    )
    
    scheduler.add_job(
        cleanup_free_plan_analytics_data,
        trigger='cron',
        hour=settings.DATA_CLEANUP_HOUR,
        minute=settings.DATA_CLEANUP_MINUTE,
        id='free_plan_data_cleanup',
        name='Free Plan Data Cleanup',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")
    
    return scheduler


async def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    """
    global scheduler
    
    if scheduler is not None:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("Scheduler shut down complete")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """
    Get the current scheduler instance.
    
    Returns:
        Current scheduler instance or None if not initialized
    """
    return scheduler


async def trigger_polar_sync() -> dict:
    """
    Manually trigger the Polar sync job.
    Useful for testing or manual runs.
    
    Returns:
        Sync results dictionary
    """
    logger.info("Manually triggering Polar sync job")
    return await sync_all_users_packages()


async def trigger_free_plan_cleanup() -> dict:
    """
    Manually trigger the free plan data cleanup job.
    Useful for testing or manual runs.
    
    Returns:
        Cleanup results dictionary
    """
    logger.info("Manually triggering free plan data cleanup")
    return await cleanup_free_plan_analytics_data()


def get_scheduler_status() -> dict:
    """
    Get the current status of the scheduler and its jobs.
    
    Returns:
        Dictionary with scheduler status information
    """
    if scheduler is None:
        return {
            "running": False,
            "jobs": []
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }