from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.admin_service import AdminService
from app.services.user_service import UserService
from app.core.config import get_settings
from app.core.security import hash_password
import hmac
import hashlib

from pathlib import Path

settings = get_settings()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(prefix="/admin", include_in_schema=False)
api_router = APIRouter(prefix="/api/admin", tags=["Admin"])

COOKIE_NAME = "fitbuddy_admin_token"


def create_admin_token(username: str) -> str:
    """Generates an HMAC-signed admin session token."""
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        username.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{username}:{signature}"


def verify_admin_token(token: str) -> bool:
    """Verifies HMAC signature on admin session token."""
    try:
        username, signature = token.split(":", 1)
        expected = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            username.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def get_current_admin(request: Request) -> str:
    """Authentication dependency ensuring request is from an authorized admin."""
    token = request.cookies.get(COOKIE_NAME)
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
            detail="Unauthorized admin session"
        )
    username = token.split(":", 1)[0]
    return username


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Renders the admin login form."""
    token = request.cookies.get(COOKIE_NAME)
    if token and verify_admin_token(token):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"error": None}
    )


@router.post("/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Authenticates admin credentials and sets session cookie."""
    admin = AdminService.authenticate_admin(db, username=username, password=password)
    if not admin:
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={"error": "Invalid username or password credentials."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    token = create_admin_token(admin.username)
    redirect = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400  # 24 hours
    )
    return redirect


@router.get("/logout", response_class=HTMLResponse)
async def admin_logout():
    """Logs out admin by invalidating session cookie."""
    redirect = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(key=COOKIE_NAME)
    return redirect


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_current_admin)
):
    """Renders the administrative dashboard with metrics and user list."""
    metrics = AdminService.get_system_metrics(db)
    users = UserService.get_all_users(db, skip=0, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "admin_user": admin_user,
            "metrics": metrics,
            "users": users
        }
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_current_admin)
):
    """Renders detailed admin view for a single user."""
    user = AdminService.get_user_with_full_details(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/user_detail.html",
        context={
            "admin_user": admin_user,
            "user": user
        }
    )


@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
async def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_current_admin)
):
    """Deletes a user and their associated records."""
    UserService.delete_user(db, user_id)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# ==========================================
# Admin REST API
# ==========================================

@api_router.get("/metrics")
def get_admin_metrics_api(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: str = Depends(get_current_admin)
):
    """Protected API endpoint returning system metrics."""
    return AdminService.get_system_metrics(db)
