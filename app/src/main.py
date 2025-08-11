from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import logging

from src.core.database import engine, get_db
from src.core.config import settings
from src.core.auth import (
    get_password_hash,
    verify_password,
    create_session,
    logout_user,
    is_authenticated,
    generate_verification_token,
    get_verification_token_expiry,
    get_current_user_id,
    get_current_user_email,
)
from src.models import Base
from src.models.email_signup import EmailSignup
from src.models.user import User
from src.models.api_key import APIKey
from src.schemas.email import EmailCreate
from src.schemas.user import UserCreate, UserLogin
from src.services.email import EmailService
from src.api.analytics import router as analytics_router
from src.api.dashboard import router as dashboard_router
from src.api.backoffice import router as backoffice_router


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
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
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


app = FastAPI(title="Klyne", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# Include API routers
app.include_router(analytics_router)
app.include_router(dashboard_router)
app.include_router(backoffice_router)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    user_authenticated = is_authenticated(request)
    user_email = get_current_user_email(request) if user_authenticated else None
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user_authenticated": user_authenticated,
            "user_email": user_email,
        },
    )


@app.post("/signup")
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


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
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
                )

                db.add(db_user)
                await db.commit()
                await db.refresh(db_user)

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


@app.get("/verify")
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


@app.get("/resend-verification", response_class=HTMLResponse)
async def resend_verification_page(request: Request):
    email = request.query_params.get("email", "")
    return templates.TemplateResponse(
        "resend_verification.html", {"request": request, "email": email}
    )


@app.post("/resend-verification")
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


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
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
            return RedirectResponse(url="/dashboard", status_code=302)

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


@app.post("/logout")
async def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
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


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    """API key management and account settings."""
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


@app.post("/api/api-keys")
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


@app.delete("/api/api-keys/{api_key_id}")
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


@app.post("/api-keys/{api_key_id}/delete")
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
