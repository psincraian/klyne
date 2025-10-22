import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import logfire
import requests
import sentry_sdk
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from src.api.analytics import router as analytics_router
from src.api.backoffice import router as backoffice_router
from src.api.dashboard import router as dashboard_router
from src.core.auth import (
    create_session,
    generate_verification_token,
    get_current_user_id,
    get_password_hash,
    get_verification_token_expiry,
    is_authenticated,
    logout_user,
    verify_password,
)
from src.core.config import settings
from src.core.database import engine, get_db
from src.core.service_dependencies import get_auth_service
from src.core.static import CachedStaticFiles
from src.core.templates import templates
from src.models import Base
from src.models.api_key import APIKey
from src.models.email_signup import EmailSignup
from src.models.user import User
from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
from src.schemas.checkout import SubscriptionInterval, SubscriptionTier
from src.schemas.email import EmailCreate
from src.schemas.user import UserCreate, UserLogin
from src.services.auth_service import AuthService
from src.services.email import EmailService
from src.services.polar import polar_service

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

# Set specific loggers
logging.getLogger("src.api.dashboard").setLevel(logging.INFO)
logging.getLogger("src.api.analytics").setLevel(logging.INFO)

# Completely disable SQLAlchemy logging
logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn="https://871a78b7650dcdede6cdbaab5417c75a@o4508215291740160.ingest.de.sentry.io/4510234680229968",
    send_default_pii=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Klyne application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(
        f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}"
    )
    logger.info(f"App Domain: {settings.APP_DOMAIN}")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    # Test bcrypt functionality on startup
    try:
        from src.core.auth import get_password_hash, verify_password

        test_hash = get_password_hash("test")
        test_verify = verify_password("test", test_hash)
        logger.info(f"Bcrypt functionality verified: {test_verify}")
    except Exception as e:
        logger.error(f"Bcrypt test failed: {str(e)}")

    # Initialize scheduler
    try:
        from src.core.scheduler import setup_scheduler

        await setup_scheduler()
        logger.info("Scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Scheduler initialization failed: {str(e)}")
        # Don't raise - scheduler is not critical for basic app functionality

    yield

    logger.info("Shutting down Klyne application...")

    # Shutdown scheduler
    try:
        from src.core.scheduler import shutdown_scheduler

        await shutdown_scheduler()
    except Exception as e:
        logger.error(f"Scheduler shutdown failed: {str(e)}")


app = FastAPI(
    title="Klyne Analytics API", lifespan=lifespan, docs_url=None, redoc_url=None
)

# configure logfire only if token exists and not using fake token
if settings.LOGFIRE_TOKEN and settings.LOGFIRE_TOKEN != "fake-token-for-testing":
    try:
        logfire.configure(token=settings.LOGFIRE_TOKEN)
        logfire.instrument_fastapi(app, capture_headers=True, excluded_urls="/healthz")
        # Instrument SQLAlchemy (async engine) so query spans are captured
        logfire.instrument_sqlalchemy(engine, capture_parameters=True)
    except Exception as e:
        logger.warning(f"Failed to configure Logfire: {e}")


# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Different CSP for development vs production
    if settings.ENVIRONMENT == "production":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com https://*.posthog.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-src https://challenges.cloudflare.com; child-src https://challenges.cloudflare.com; worker-src https://challenges.cloudflare.com; connect-src 'self' https://challenges.cloudflare.com https://*.posthog.com"
        )
    else:
        # More permissive CSP for development (allows Vite HMR)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* ws: wss: https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline' localhost:*; img-src 'self' data: localhost:*; font-src 'self' localhost:*; frame-src https://challenges.cloudflare.com; child-src https://challenges.cloudflare.com; worker-src https://challenges.cloudflare.com; connect-src 'self' localhost:* ws: wss: https://challenges.cloudflare.com"
        )
    return response


# HTTPS redirect handled at proxy/load balancer level
# Commented out to prevent redirect loops in containerized environments
# if settings.ENVIRONMENT == "production":
#     app.add_middleware(HTTPSRedirectMiddleware)

# Add trusted host middleware for production
if (
    settings.ENVIRONMENT == "production"
    and hasattr(settings, "APP_DOMAIN")
    and settings.APP_DOMAIN
):
    from urllib.parse import urlparse

    parsed_domain = urlparse(settings.APP_DOMAIN)
    allowed_host = parsed_domain.netloc if parsed_domain.netloc else settings.APP_DOMAIN
    # Also allow localhost for health checks in containerized environments
    allowed_hosts = [allowed_host, "localhost", "localhost:8000"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=31536000,  # 1 year (365 days * 24 hours * 60 minutes * 60 seconds)
    same_site="strict",
    https_only=(settings.ENVIRONMENT == "production"),
)
app.mount("/static", CachedStaticFiles(directory="src/static/dist"), name="static")
# Additional mount for fonts referenced directly by CSS
app.mount("/fonts", CachedStaticFiles(directory="src/static/dist/fonts"), name="fonts")
# Mount public folder with 7-day caching (604800 seconds)
app.mount(
    "/public",
    CachedStaticFiles(directory="src/static/public", max_age=604800),
    name="public",
)

# Use shared templates instance with asset management functions

# Include API routers
app.include_router(analytics_router)
app.include_router(dashboard_router, include_in_schema=False)
app.include_router(backoffice_router, include_in_schema=False)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(
    request: Request, auth_service: AuthService = Depends(get_auth_service)
):
    user = await auth_service.get_current_user_if_authenticated(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.post("/signup", include_in_schema=False)
async def signup(
    request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)
):
    try:
        email_obj = EmailCreate(email=email)

        existing = await db.execute(
            select(EmailSignup).filter(EmailSignup.email == email_obj.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        db_email = EmailSignup(email=email_obj.email)
        db.add(db_email)
        await db.commit()

        return templates.TemplateResponse(
            "success.html", {"request": request, "email": email}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/analytics", status_code=302)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "CF_TURNSTILE_SITE_KEY": settings.CF_TURNSTILE_SITE_KEY},
    )


def validate_turnstile(token, secret, remoteip=None) -> bool:
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    data = {"secret": secret, "response": token}

    if remoteip:
        data["remoteip"] = remoteip

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return response.json().get("success", False)
    except requests.RequestException as e:
        print(f"Turnstile validation error: {e}")
        return False


@app.post("/register", include_in_schema=False)
async def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    cf_turnstile_response: str = Form(..., alias="cf-turnstile-response"),
    db: AsyncSession = Depends(get_db),
):
    error_message = None

    token = cf_turnstile_response
    remoteip = (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For")
        or request.client.host
    )

    try:
        if password != password_confirm:
            error_message = "Passwords do not match"
        elif len(password) < 8:
            error_message = "Password must be at least 8 characters"
        elif not validate_turnstile(token, settings.CF_TURNSTILE_SECRET, remoteip):
            error_message = "Bot validation failed"
        else:
            user_data = UserCreate(email=email, password=password)

            existing_user = await db.execute(
                select(User).filter(User.email == user_data.email)
            )
            if existing_user.scalar_one_or_none():
                error_message = "An account with this email already exists"
            else:
                verification_token = generate_verification_token()
                token_expiry = get_verification_token_expiry()

                db_user = User(
                    email=user_data.email,
                    hashed_password=get_password_hash(user_data.password),
                    verification_token=verification_token,
                    verification_token_expires=token_expiry,
                    is_verified=False,
                    is_admin=False,  # Explicitly set is_admin to handle cloud database
                )

                db.add(db_user)
                await db.commit()
                await db.refresh(db_user)

                # Create customer in Polar with user ID as external customer ID
                polar_customer_id = await polar_service.create_customer(
                    email=user_data.email, external_customer_id=str(db_user.id)
                )
                if polar_customer_id:
                    logger.info(
                        f"Created Polar customer {polar_customer_id} for user {db_user.id}"
                    )
                else:
                    logger.warning(
                        f"Failed to create Polar customer for user {db_user.id}"
                    )

                # Send verification email
                uow = SqlAlchemyUnitOfWork(db)
                email_service = EmailService(uow)
                await email_service.send_verification_email(
                    user_data.email, verification_token, user_id=db_user.id
                )

                return templates.TemplateResponse(
                    "registration_success.html",
                    {"request": request, "email": user_data.email},
                )

    except Exception as e:
        await db.rollback()
        logger.error(f"Registration failed for {email}: {str(e)}", exc_info=True)
        error_message = "Registration failed. Please try again."

    # If we got here, there was an error - show the form again with the error
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "error_message": error_message,
            "email": email,
            "password": password,
            "password_confirm": password_confirm,
        },
        status_code=400,
    )


@app.get("/verify", include_in_schema=False)
async def verify_email(
    request: Request, token: str, db: AsyncSession = Depends(get_db)
):
    try:
        user = await db.execute(
            select(User).filter(
                User.verification_token == token,
                User.verification_token_expires > datetime.now(timezone.utc),
            )
        )
        user = user.scalar_one_or_none()

        if not user:
            # Check if token exists but is expired
            expired_user = await db.execute(
                select(User).filter(User.verification_token == token)
            )
            expired_user = expired_user.scalar_one_or_none()

            if expired_user:
                error_message = "Your verification link has expired. Please request a new verification email."
                show_resend = True
                email = expired_user.email
            else:
                error_message = "Invalid verification link. Please check your email or register again."
                show_resend = False
                email = None

            return templates.TemplateResponse(
                "verification_error.html",
                {
                    "request": request,
                    "error_message": error_message,
                    "show_resend": show_resend,
                    "email": email,
                },
                status_code=400,
            )

        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None

        await db.commit()

        return templates.TemplateResponse(
            "verification_success.html", {"request": request}
        )

    except Exception:
        error_message = "Verification failed. Please try again or contact support."
        return templates.TemplateResponse(
            "verification_error.html",
            {"request": request, "error_message": error_message, "show_resend": False},
            status_code=400,
        )


@app.get("/resend-verification", response_class=HTMLResponse, include_in_schema=False)
async def resend_verification_page(request: Request):
    email = request.query_params.get("email", "")
    return templates.TemplateResponse(
        "resend_verification.html", {"request": request, "email": email}
    )


@app.post("/resend-verification", include_in_schema=False)
async def resend_verification(
    request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)
):
    try:
        # Find the user by email
        user = await db.execute(select(User).filter(User.email == email))
        user = user.scalar_one_or_none()

        if not user:
            # Don't reveal if email exists or not for security
            return templates.TemplateResponse(
                "resend_verification_success.html",
                {"request": request, "email": email},
            )

        if user.is_verified:
            # User is already verified
            return templates.TemplateResponse(
                "resend_verification_already_verified.html",
                {"request": request, "email": email},
            )

        # Generate new verification token
        verification_token = generate_verification_token()
        token_expiry = get_verification_token_expiry()

        user.verification_token = verification_token
        user.verification_token_expires = token_expiry

        await db.commit()

        # Send new verification email
        uow = SqlAlchemyUnitOfWork(db)
        email_service = EmailService(uow)
        await email_service.send_verification_email(
            email, verification_token, user_id=user.id
        )

        return templates.TemplateResponse(
            "resend_verification_success.html",
            {"request": request, "email": email},
        )

    except Exception as e:
        logger.error(f"Failed to resend verification email: {str(e)}")
        # Don't reveal errors for security
        return templates.TemplateResponse(
            "resend_verification_success.html",
            {"request": request, "email": email},
        )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/analytics", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", include_in_schema=False)
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    error_message = None

    try:
        user_data = UserLogin(email=email, password=password)

        user = await db.execute(select(User).filter(User.email == user_data.email))
        user = user.scalar_one_or_none()

        if not user or not verify_password(user_data.password, user.hashed_password):
            error_message = "Invalid email or password"
            show_resend = False
        elif not user.is_verified:
            error_message = "Please verify your email before logging in. Check your inbox for the verification link."
            show_resend = True
        elif not user.is_active:
            error_message = "Your account has been deactivated. Please contact support for assistance."
            show_resend = False
        else:
            create_session(request, user.id, user.email)
            return RedirectResponse(url="/analytics", status_code=302)

    except Exception:
        error_message = "Login failed. Please try again."
        show_resend = False

    # If we got here, there was an error - show the form again with the error
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error_message": error_message,
            "email": email,
            "show_resend": show_resend,
        },
        status_code=400,
    )


@app.post("/logout", include_in_schema=False)
async def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/", status_code=302)


@app.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
async def analytics_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Analytics dashboard with charts and metrics."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    user_id = get_current_user_id(request)
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        logout_user(request)
        return RedirectResponse(url="/login", status_code=302)

    # Get user's API keys
    api_keys_result = await db.execute(select(APIKey).filter(APIKey.user_id == user_id))
    api_keys = api_keys_result.scalars().all()

    # Get package usage information
    from src.core.subscription_utils import get_user_package_usage

    current_count, limit = await get_user_package_usage(db, user_id)

    package_usage = {
        "current": current_count,
        "limit": limit,
        "tier": user.subscription_tier or "none",
    }

    return templates.TemplateResponse(
        "analytics-dashboard.html",
        {
            "request": request,
            "user": user,
            "api_keys": api_keys,
            "package_usage": package_usage,
        },
    )


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Account settings and API key management."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    user_id = get_current_user_id(request)
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        logout_user(request)
        return RedirectResponse(url="/login", status_code=302)

    # Get user's API keys
    api_keys_result = await db.execute(select(APIKey).filter(APIKey.user_id == user_id))
    api_keys = api_keys_result.scalars().all()

    # Get package usage information
    from src.core.subscription_utils import (
        can_user_create_package,
        get_user_package_usage,
    )

    current_count, limit = await get_user_package_usage(db, user_id)
    can_create, error_message, _, _ = await can_user_create_package(db, user_id)

    package_usage = {
        "current": current_count,
        "limit": limit,
        "can_create": can_create,
        "error_message": error_message,
        "tier": user.subscription_tier or "none",
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "api_keys": api_keys,
            "package_usage": package_usage,
        },
    )


@app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Account settings and preferences."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    user_id = get_current_user_id(request)
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        logout_user(request)
        return RedirectResponse(url="/login", status_code=302)

    # Get user's API keys for usage statistics
    api_keys_result = await db.execute(select(APIKey).filter(APIKey.user_id == user_id))
    api_keys = api_keys_result.scalars().all()

    return templates.TemplateResponse(
        "settings.html", {"request": request, "user": user, "api_keys": api_keys}
    )


@app.get("/pricing", response_class=HTMLResponse, include_in_schema=False)
async def pricing_page(
    request: Request, auth_service: AuthService = Depends(get_auth_service)
):
    """Pricing information."""
    user = await auth_service.get_current_user_if_authenticated(request)

    subscription_info = {
        "active": user.subscription_status == "active" if user else False,
        "subscriptions": [user.subscription_tier] if user else [],
    }

    return templates.TemplateResponse(
        "pricing.html",
        {"request": request, "user": user, "subscription_info": subscription_info},
    )


@app.post("/api/checkout", include_in_schema=False)
async def checkout(
    request: Request,
    tier: str = Form(...),
    interval: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Create checkout session for subscription plan."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate the parameters
    try:
        subscription_tier = SubscriptionTier(tier.lower())
        subscription_interval = SubscriptionInterval(interval.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier or interval")

    # Get the appropriate product ID
    product_id = None
    if (
        subscription_tier == SubscriptionTier.STARTER
        and subscription_interval == SubscriptionInterval.MONTHLY
    ):
        product_id = settings.POLAR_STARTER_MONTHLY_PRODUCT_ID
    elif (
        subscription_tier == SubscriptionTier.STARTER
        and subscription_interval == SubscriptionInterval.YEARLY
    ):
        product_id = settings.POLAR_STARTER_YEARLY_PRODUCT_ID
    elif (
        subscription_tier == SubscriptionTier.PRO
        and subscription_interval == SubscriptionInterval.MONTHLY
    ):
        product_id = settings.POLAR_PRO_MONTHLY_PRODUCT_ID
    elif (
        subscription_tier == SubscriptionTier.PRO
        and subscription_interval == SubscriptionInterval.YEARLY
    ):
        product_id = settings.POLAR_PRO_YEARLY_PRODUCT_ID

    if not product_id:
        raise HTTPException(
            status_code=500,
            detail=f"{subscription_tier.value.title()} {subscription_interval.value} plan not configured",
        )

    try:
        checkout_url = await polar_service.create_checkout_session(
            product_id=product_id,
            external_customer_id=str(user_id),
            success_url=f"{settings.APP_DOMAIN}/checkout/confirmation?plan={subscription_tier.value}&interval={subscription_interval.value}&user_id={user_id}",
        )

        if not checkout_url:
            raise HTTPException(
                status_code=500, detail="Failed to create checkout session"
            )

        return RedirectResponse(url=checkout_url, status_code=302)

    except Exception as e:
        logger.error(
            f"Failed to create {subscription_tier.value} {subscription_interval.value} checkout for user {user_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/api/customer-portal", include_in_schema=False)
async def customer_portal_redirect(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """Redirect authenticated users to the Polar customer portal."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        portal_url = await polar_service.get_customer_portal_url(str(user_id))

        if not portal_url:
            raise HTTPException(
                status_code=500, detail="Failed to create customer portal session"
            )

        return RedirectResponse(url=portal_url, status_code=302)

    except Exception as e:
        logger.error(f"Failed to redirect to customer portal for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to access customer portal")


@app.get("/checkout/confirmation", response_class=HTMLResponse, include_in_schema=False)
async def checkout_confirmation(
    request: Request,
    plan: str = "starter",
    interval: str = "monthly",
    auth_service: AuthService = Depends(get_auth_service),
):
    """Checkout confirmation page that waits for subscription activation."""

    # First try to get user from session
    user = None
    if is_authenticated(request):
        user = await auth_service.get_current_user_if_authenticated(request)

    # If still no user, redirect to login
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Validate plan parameter
    if plan not in ["starter", "pro"]:
        plan = "starter"

    # Validate interval parameter
    if interval not in ["monthly", "yearly"]:
        interval = "monthly"

    plan_name = f"{plan.title()} ({interval.title()})"

    return templates.TemplateResponse(
        "checkout_confirmation.html",
        {"request": request, "user": user, "plan_name": plan_name},
    )


@app.get("/api/subscription-status", include_in_schema=False)
async def get_subscription_status(request: Request, db: AsyncSession = Depends(get_db)):
    """API endpoint to check current user's subscription status."""

    # Get user_id from session or parameter
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get user from database
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": user.subscription_status,
        "tier": user.subscription_tier,
        "updated_at": user.subscription_updated_at.isoformat()
        if user.subscription_updated_at
        else None,
    }


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page(
    request: Request, auth_service: AuthService = Depends(get_auth_service)
):
    """Documentation."""
    user = await auth_service.get_current_user_if_authenticated(request)
    return templates.TemplateResponse("docs.html", {"request": request, "user": user})


@app.post("/api/api-keys", include_in_schema=False)
async def create_api_key(
    request: Request, package_name: str = Form(...), db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(request)

    # Check subscription limits before creating API key
    from src.core.subscription_utils import can_user_create_package

    can_create, error_message, current_count, limit = await can_user_create_package(
        db, user_id
    )

    if not can_create:
        raise HTTPException(status_code=403, detail=error_message)

    # Check if package name already exists for this user
    existing_key = await db.execute(
        select(APIKey).filter(
            APIKey.user_id == user_id, APIKey.package_name == package_name
        )
    )
    if existing_key.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="API key for this package already exists"
        )

    # Create new API key
    api_key = APIKey(
        package_name=package_name, key=APIKey.generate_key(), user_id=user_id
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Count total API keys for this user after creation
    api_keys_count_result = await db.execute(
        select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
    )
    packages_count = api_keys_count_result.scalar()

    # Ingest event to Polar
    from src.services.polar import polar_service

    await polar_service.ingest_event(
        event_name="packages",
        external_customer_id=str(user_id),
        metadata={"packagesCount": packages_count},
    )

    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/api/api-keys/{api_key_id}/regenerate", include_in_schema=False)
async def regenerate_api_key(
    request: Request, api_key_id: int, db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(request)

    # Get the API key and verify ownership
    api_key = await db.execute(
        select(APIKey).filter(APIKey.id == api_key_id, APIKey.user_id == user_id)
    )
    api_key = api_key.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Generate new key using the same logic as the original creation
    new_key = APIKey.generate_key()
    api_key.key = new_key
    await db.commit()
    await db.refresh(api_key)

    return {"success": True, "new_key": new_key}


@app.delete("/api/api-keys/{api_key_id}", include_in_schema=False)
async def delete_api_key(
    request: Request, api_key_id: int, db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(request)

    # Get the API key and verify ownership
    api_key = await db.execute(
        select(APIKey).filter(APIKey.id == api_key_id, APIKey.user_id == user_id)
    )
    api_key = api_key.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(api_key)
    await db.commit()

    # Count total API keys for this user after deletion
    api_keys_count_result = await db.execute(
        select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
    )
    packages_count = api_keys_count_result.scalar()

    # Ingest event to Polar
    from src.services.polar import polar_service

    await polar_service.ingest_event(
        event_name="packages",
        external_customer_id=str(user_id),
        metadata={"packagesCount": packages_count},
    )

    return {"success": True}


@app.post("/api-keys/{api_key_id}/delete", include_in_schema=False)
async def delete_api_key_form(
    request: Request, api_key_id: int, db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    user_id = get_current_user_id(request)

    # Get the API key and verify ownership
    api_key = await db.execute(
        select(APIKey).filter(APIKey.id == api_key_id, APIKey.user_id == user_id)
    )
    api_key = api_key.scalar_one_or_none()

    if api_key:
        await db.delete(api_key)
        await db.commit()

        # Count total API keys for this user after deletion
        api_keys_count_result = await db.execute(
            select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
        )
        packages_count = api_keys_count_result.scalar()

        # Ingest event to Polar
        from src.services.polar import polar_service

        await polar_service.ingest_event(
            event_name="packages",
            external_customer_id=str(user_id),
            metadata={"packagesCount": packages_count},
        )

    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/webhooks/polar", include_in_schema=False)
async def polar_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Polar webhook events."""
    try:
        # Get the webhook payload
        body = await request.body()

        # TODO: Verify webhook signature using POLAR_WEBHOOK_SECRET
        # For now, we'll proceed without signature verification

        # Parse JSON payload
        import json

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Failed to parse webhook payload as JSON")
            return {"error": "Invalid JSON"}, 400

        event_type = payload.get("type")
        event_data = payload.get("data", {})

        # Only handle subscription events we care about
        if event_type not in ["subscription.active", "subscription.canceled"]:
            logger.info(f"Ignoring webhook event type: {event_type}")
            return {"status": "ignored"}

        # Get external customer ID from the subscription
        external_customer_id = event_data.get("customer", {}).get("external_id")
        if not external_customer_id:
            logger.error("No external_customer_id found in webhook payload")
            return {"error": "Missing external_customer_id"}, 400

        # Find the user by external customer ID (user.id)
        try:
            user_id = int(external_customer_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid external_customer_id: {external_customer_id}")
            return {"error": "Invalid external_customer_id"}, 400

        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.error(
                f"User not found for external_customer_id: {external_customer_id}"
            )
            return {"error": "User not found"}, 404

        # Update user subscription status based on event type
        if event_type == "subscription.active":
            user.subscription_status = "active"
            # Extract subscription tier from product name or ID
            product = event_data.get("product", {})
            product_name = product.get("name", "").lower()
            if "starter" in product_name:
                user.subscription_tier = "starter"
            elif "pro" in product_name:
                user.subscription_tier = "pro"
            else:
                # Fallback to extracting from product ID configuration
                product_id = product.get("id")
                if product_id in [
                    settings.POLAR_STARTER_MONTHLY_PRODUCT_ID,
                    settings.POLAR_STARTER_YEARLY_PRODUCT_ID,
                ]:
                    user.subscription_tier = "starter"
                elif product_id in [
                    settings.POLAR_PRO_MONTHLY_PRODUCT_ID,
                    settings.POLAR_PRO_YEARLY_PRODUCT_ID,
                ]:
                    user.subscription_tier = "pro"
                else:
                    user.subscription_tier = "unknown"

            logger.info(
                f"Activated {user.subscription_tier} subscription for user {user_id}"
            )

        elif event_type == "subscription.canceled":
            user.subscription_status = "canceled"
            # Keep the tier for historical purposes, just change status
            logger.info(f"Canceled subscription for user {user_id}")

        # Update the timestamp
        from datetime import datetime, timezone

        user.subscription_updated_at = datetime.now(timezone.utc)

        await db.commit()

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing Polar webhook: {e}", exc_info=True)
        await db.rollback()
        return {"error": "Internal server error"}, 500


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "healthy"}


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
    """Serve robots.txt for SEO."""
    with open("src/static/robots.txt", "r") as f:
        return f.read()


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    """Serve sitemap.xml for SEO."""
    with open("src/static/sitemap.xml", "r") as f:
        content = f.read()
    return Response(content=content, media_type="application/xml")


@app.get("/scheduler/status", include_in_schema=False)
async def scheduler_status():
    """Get the current status of the scheduler and its jobs."""
    try:
        from src.core.scheduler import get_scheduler_status

        return get_scheduler_status()
    except Exception as e:
        return {"error": str(e)}


@app.post("/scheduler/trigger-sync", include_in_schema=False)
async def trigger_sync():
    """Manually trigger the Polar package sync."""
    try:
        from src.core.scheduler import trigger_polar_sync

        results = await trigger_polar_sync()
        return results
    except Exception as e:
        return {"error": str(e)}


@app.post("/scheduler/trigger-welcome-emails", include_in_schema=False)
async def trigger_welcome_emails():
    """Manually trigger the welcome email task."""
    try:
        from src.core.scheduler import trigger_welcome_emails

        results = await trigger_welcome_emails()
        return results
    except Exception as e:
        return {"error": str(e)}
