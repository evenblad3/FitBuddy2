from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.user_service import UserService
from app.services.workout_service import WorkoutService
from app.services.feedback_service import FeedbackService
from app.services.nutrition_service import NutritionService
from app.schemas.user import UserCreate, FitnessGoalEnum, IntensityEnum, ExperienceLevelEnum

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Renders the landing home page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_create_page(request: Request):
    """Renders the fitness profile creation form."""
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"form_data": None, "error": None}
    )


@router.post("/profile", response_class=HTMLResponse)
async def profile_create_submit(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    experience_level: str = Form("Beginner"),
    db: Session = Depends(get_db)
):
    """Processes profile form submission and redirects to user view."""
    form_data = {
        "name": name,
        "age": age,
        "weight": weight,
        "goal": goal,
        "intensity": intensity,
        "experience_level": experience_level
    }
    try:
        user_in = UserCreate(
            name=name,
            age=age,
            weight=weight,
            goal=FitnessGoalEnum(goal),
            intensity=IntensityEnum(intensity),
            experience_level=ExperienceLevelEnum(experience_level)
        )
        user = UserService.create_user(db, user_in)
        return RedirectResponse(url=f"/profile/{user.id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context={"form_data": form_data, "error": str(e)},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@router.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile_detail_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Displays user profile details and their generated plans."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return templates.TemplateResponse(
        request=request,
        name="profile_view.html",
        context={"user": user}
    )


@router.get("/workout/generate/{user_id}", response_class=HTMLResponse)
async def workout_generate_transition_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Renders loading transition while preparing AI generation."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return templates.TemplateResponse(
        request=request,
        name="generating.html",
        context={"user": user}
    )


@router.get("/workout/do-generate/{user_id}", response_class=HTMLResponse)
async def workout_do_generate_action(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Invokes Gemini workout generation and redirects to result page."""
    try:
        plan = WorkoutService.generate_plan_for_user(db, user_id)
        return RedirectResponse(url=f"/workout/{plan.id}", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Generation failed: {str(e)}")


@router.get("/workout/{plan_id}", response_class=HTMLResponse)
async def workout_result_page(request: Request, plan_id: int, db: Session = Depends(get_db)):
    """Renders the 7-day structured workout plan."""
    plan = WorkoutService.get_plan_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
    user = UserService.get_user_by_id(db, plan.user_id)
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "workout_plan": plan,
            "plan_data": plan.current_plan_dict,
            "user": user
        }
    )


@router.get("/workout/{plan_id}/feedback", response_class=HTMLResponse)
async def workout_feedback_page(request: Request, plan_id: int, db: Session = Depends(get_db)):
    """Renders the feedback form for refining a plan."""
    plan = WorkoutService.get_plan_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
    user = UserService.get_user_by_id(db, plan.user_id)
    feedbacks = FeedbackService.get_feedback_for_plan(db, plan_id)
    return templates.TemplateResponse(
        request=request,
        name="feedback.html",
        context={
            "workout_plan": plan,
            "plan_data": plan.current_plan_dict,
            "user": user,
            "feedbacks": feedbacks,
            "error": None
        }
    )


@router.post("/workout/{plan_id}/feedback", response_class=HTMLResponse)
async def workout_feedback_submit(
    request: Request,
    plan_id: int,
    feedback: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processes feedback submission and redirects to refined plan."""
    try:
        FeedbackService.submit_feedback_and_update_plan(
            db=db,
            workout_plan_id=plan_id,
            feedback_text=feedback
        )
        return RedirectResponse(url=f"/workout/{plan_id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        plan = WorkoutService.get_plan_by_id(db, plan_id)
        user = UserService.get_user_by_id(db, plan.user_id) if plan else None
        feedbacks = FeedbackService.get_feedback_for_plan(db, plan_id) if plan else []
        return templates.TemplateResponse(
            request=request,
            name="feedback.html",
            context={
                "workout_plan": plan,
                "plan_data": plan.current_plan_dict if plan else {},
                "user": user,
                "feedbacks": feedbacks,
                "error": str(e)
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )


@router.get("/nutrition", response_class=HTMLResponse)
async def nutrition_page(request: Request, db: Session = Depends(get_db)):
    """Renders the nutrition and recovery guide page."""
    recent_tips = NutritionService.get_recent_tips(db, limit=10)
    return templates.TemplateResponse(
        request=request,
        name="nutrition.html",
        context={"recent_tips": recent_tips}
    )


@router.get("/history/{user_id}", response_class=HTMLResponse)
async def workout_history_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Displays user's historical workout plans."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    plans = WorkoutService.get_plans_by_user_id(db, user_id)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"user": user, "plans": plans}
    )



