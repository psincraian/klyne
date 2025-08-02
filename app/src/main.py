from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import engine, get_db
from src.models import Base
from src.models.email_signup import EmailSignup
from src.schemas.email import EmailCreate


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Klyne", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}