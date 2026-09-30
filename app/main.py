from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import logger
from app.db.database import init_db
from app.routers import web, api

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    logger.info("Starting FitBuddy Application...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield
    logger.info("FitBuddy Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Personalized Fitness Planning & Nutrition Web Application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Static files mounting
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Root health alias
@app.get("/health", tags=["Health"])
def root_health():
    return {"status": "ok", "app": settings.APP_NAME}


from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


# Custom Exception Handlers for clean user and API experiences
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.headers and "Location" in exc.headers:
        return RedirectResponse(
            url=exc.headers["Location"],
            status_code=exc.status_code
        )
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": f"Error {exc.status_code}",
            "message": exc.detail,
            "error_details": None,
            "debug": settings.DEBUG,
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": jsonable_encoder(exc.errors())},
        )
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": "Validation Error",
            "message": "The information provided was invalid. Please check your inputs.",
            "error_details": str(exc.errors()),
            "debug": settings.DEBUG,
        },
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please try again later."},
        )
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": "Internal Server Error",
            "message": "We encountered an unexpected problem. Our team has been notified.",
            "error_details": str(exc) if settings.DEBUG else None,
            "debug": settings.DEBUG,
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


from app.routers import web, api, admin


# Include Routers
app.include_router(web.router)
app.include_router(api.router)
app.include_router(admin.router)
app.include_router(admin.api_router)
