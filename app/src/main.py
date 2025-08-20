import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
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
from src.models import Base
from src.models.api_key import APIKey
from src.models.email_signup import EmailSignup
from src.models.user import User
from src.schemas.email import EmailCreate
from src.schemas.user import UserCreate, UserLogin
from src.services.email import EmailService
from src.services.polar import polar_service


async def get_current_user_if_authenticated(
    request: Request, db: AsyncSession
) -> User | None:
    """Helper function to get the current user if authenticated, None otherwise."""
    if not is_authenticated(request):
        return None

    user_id = get_current_user_id(request)
    if not user_id:
        return None

    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()


async def require_active_subscription(request: Request, db: AsyncSession) -> User:
    """Require user to be authenticated and have an active subscription."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")

    return user


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

    yield
    logger.info("Shutting down Klyne application...")


app = FastAPI(
    title="Klyne Analytics API", lifespan=lifespan, docs_url=None, redoc_url=None
)


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
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
        )
    else:
        # More permissive CSP for development (allows Vite HMR)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* ws: wss:; style-src 'self' 'unsafe-inline' localhost:*; img-src 'self' data: localhost:*; font-src 'self' localhost:*; connect-src 'self' localhost:* ws: wss:"
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
    max_age=3600,
    same_site="strict",
    https_only=(settings.ENVIRONMENT == "production"),
)
app.mount("/static", StaticFiles(directory="src/static/dist"), name="static")
# Additional mount for fonts referenced directly by CSS
app.mount("/fonts", StaticFiles(directory="src/static/dist/fonts"), name="fonts")

# Use shared templates instance with asset management functions
from src.core.templates import templates

# Include API routers
app.include_router(analytics_router)
app.include_router(dashboard_router, include_in_schema=False)
app.include_router(backoffice_router, include_in_schema=False)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_if_authenticated(request, db)
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
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", include_in_schema=False)
async def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    error_message = None

    try:
        if password != password_confirm:
            error_message = "Passwords do not match"
        elif len(password) < 8:
            error_message = "Password must be at least 8 characters"
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

                await EmailService.send_verification_email(
                    user_data.email, verification_token
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
        await EmailService.send_verification_email(email, verification_token)

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

    return templates.TemplateResponse(
        "analytics-dashboard.html",
        {"request": request, "user": user, "api_keys": api_keys},
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

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "api_keys": api_keys}
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
async def pricing_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Pricing information."""
    user = await get_current_user_if_authenticated(request, db)

    subscription_info = {
        "active": user.subscription_status == "active" if user else False,
        "subscriptions": [user.subscription_tier] if user else [],
    }

    return templates.TemplateResponse(
        "pricing.html",
        {"request": request, "user": user, "subscription_info": subscription_info},
    )


@app.post("/api/checkout/starter", include_in_schema=False)
async def checkout_starter(request: Request, db: AsyncSession = Depends(get_db)):
    """Create checkout session for Starter plan."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not settings.POLAR_STARTER_PRODUCT_ID:
        raise HTTPException(status_code=500, detail="Starter plan not configured")

    try:
        checkout_url = await polar_service.create_checkout_session(
            product_id=settings.POLAR_STARTER_PRODUCT_ID,
            external_customer_id=str(user_id),
            success_url=f"{settings.APP_DOMAIN}/checkout/confirmation?plan=starter&user_id={user_id}",
        )

        if not checkout_url:
            raise HTTPException(
                status_code=500, detail="Failed to create checkout session"
            )

        return RedirectResponse(url=checkout_url, status_code=302)

    except Exception as e:
        logger.error(f"Failed to create starter checkout for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/api/checkout/pro", include_in_schema=False)
async def checkout_pro(request: Request, db: AsyncSession = Depends(get_db)):
    """Create checkout session for Pro plan."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not settings.POLAR_PRO_PRODUCT_ID:
        raise HTTPException(status_code=500, detail="Pro plan not configured")

    try:
        checkout_url = await polar_service.create_checkout_session(
            product_id=settings.POLAR_PRO_PRODUCT_ID,
            external_customer_id=str(user_id),
            success_url=f"{settings.APP_DOMAIN}/checkout/confirmation?plan=pro&user_id={user_id}",
        )

        if not checkout_url:
            raise HTTPException(
                status_code=500, detail="Failed to create checkout session"
            )

        return RedirectResponse(url=checkout_url, status_code=302)

    except Exception as e:
        logger.error(f"Failed to create pro checkout for user {user_id}: {e}")
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
    request: Request, plan: str = "starter", db: AsyncSession = Depends(get_db)
):
    """Checkout confirmation page that waits for subscription activation."""

    # First try to get user from session
    user = None
    if is_authenticated(request):
        user = await get_current_user_if_authenticated(request, db)

    # If still no user, redirect to login
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Validate plan parameter
    if plan not in ["starter", "pro"]:
        plan = "starter"

    plan_name = plan.title()

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
async def documentation_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Documentation."""
    user = await get_current_user_if_authenticated(request, db)
    return templates.TemplateResponse("docs.html", {"request": request, "user": user})


@app.post("/api/api-keys", include_in_schema=False)
async def create_api_key(
    request: Request, package_name: str = Form(...), db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(request)

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

    return RedirectResponse(url="/dashboard", status_code=302)


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
                if product_id == settings.POLAR_STARTER_PRODUCT_ID:
                    user.subscription_tier = "starter"
                elif product_id == settings.POLAR_PRO_PRODUCT_ID:
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
