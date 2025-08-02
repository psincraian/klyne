from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from src.core.database import engine, get_db
from src.core.config import settings
from src.core.auth import (
    get_password_hash, verify_password, create_session, 
    logout_user, is_authenticated, generate_verification_token,
    get_verification_token_expiry, get_current_user_id, get_current_user_email
)
from src.models import Base
from src.models.email_signup import EmailSignup
from src.models.user import User
from src.schemas.email import EmailCreate
from src.schemas.user import UserCreate, UserLogin
from src.services.email import EmailService


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Klyne", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    user_authenticated = is_authenticated(request)
    user_email = get_current_user_email(request) if user_authenticated else None
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user_authenticated": user_authenticated,
        "user_email": user_email
    })


@app.post("/signup")
async def signup(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)):
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
            "success.html", 
            {"request": request, "email": email}
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
    db: AsyncSession = Depends(get_db)
):
    try:
        if password != password_confirm:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        user_data = UserCreate(email=email, password=password)
        
        existing_user = await db.execute(
            select(User).filter(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        verification_token = generate_verification_token()
        token_expiry = get_verification_token_expiry()
        
        db_user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            verification_token=verification_token,
            verification_token_expires=token_expiry,
            is_verified=False
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        await EmailService.send_verification_email(user_data.email, verification_token)
        
        return templates.TemplateResponse(
            "registration_success.html",
            {"request": request, "email": user_data.email}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")


@app.get("/verify")
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await db.execute(
            select(User).filter(
                User.verification_token == token,
                User.verification_token_expires > datetime.now(timezone.utc)
            )
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        
        await db.commit()
        
        return templates.TemplateResponse(
            "verification_success.html",
            {"request": request}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Verification failed")


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
    db: AsyncSession = Depends(get_db)
):
    try:
        user_data = UserLogin(email=email, password=password)
        
        user = await db.execute(
            select(User).filter(User.email == user_data.email)
        )
        user = user.scalar_one_or_none()
        
        if not user or not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid email or password")
        
        if not user.is_verified:
            raise HTTPException(status_code=400, detail="Please verify your email before logging in")
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Account is deactivated")
        
        create_session(request, user.id, user.email)
        
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")


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
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}