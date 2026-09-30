from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.core.config import get_settings
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.workout import WorkoutGenerateRequest, WorkoutPlanResponse, WorkoutPlanContentSchema
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.nutrition import NutritionTipRequest, NutritionTipResponse
from app.services.user_service import UserService
from app.services.workout_service import WorkoutService
from app.services.feedback_service import FeedbackService
from app.services.nutrition_service import NutritionService

settings = get_settings()
router = APIRouter(prefix="/api", tags=["General"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying application and database connectivity."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }


# ==========================================
# User Endpoints
# ==========================================

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user_endpoint(user_in: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user fitness profile."""
    return UserService.create_user(db, user_in)


@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Retrieves user profile by ID."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return user


@router.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users_endpoint(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    """Lists users with pagination."""
    return UserService.get_all_users(db, skip=skip, limit=limit)


# ==========================================
# Workout Plan Endpoints
# ==========================================

@router.post("/workouts/generate", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED, tags=["Workouts"])
def generate_workout_endpoint(payload: WorkoutGenerateRequest, db: Session = Depends(get_db)):
    """Generates a personalized 7-day workout plan using Gemini AI."""
    try:
        plan = WorkoutService.generate_plan_for_user(db, payload.user_id)
        return WorkoutPlanResponse(
            id=plan.id,
            user_id=plan.user_id,
            goal=plan.goal,
            intensity=plan.intensity,
            current_plan=WorkoutPlanContentSchema.model_validate(plan.current_plan_dict),
            version=plan.version,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate workout plan: {str(e)}")


@router.get("/workouts/{plan_id}", response_model=WorkoutPlanResponse, tags=["Workouts"])
def get_workout_endpoint(plan_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific workout plan by ID."""
    plan = WorkoutService.get_plan_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workout plan #{plan_id} not found.")
    return WorkoutPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        goal=plan.goal,
        intensity=plan.intensity,
        current_plan=WorkoutPlanContentSchema.model_validate(plan.current_plan_dict),
        version=plan.version,
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )


@router.get("/workouts/user/{user_id}", response_model=List[WorkoutPlanResponse], tags=["Workouts"])
def get_user_workouts_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Retrieves all workout plans for a given user."""
    plans = WorkoutService.get_plans_by_user_id(db, user_id)
    return [
        WorkoutPlanResponse(
            id=p.id,
            user_id=p.user_id,
            goal=p.goal,
            intensity=p.intensity,
            current_plan=WorkoutPlanContentSchema.model_validate(p.current_plan_dict),
            version=p.version,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in plans
    ]


# ==========================================
# Feedback Endpoints
# ==========================================

@router.post("/workouts/{plan_id}/feedback", response_model=WorkoutPlanResponse, tags=["Feedback"])
def submit_feedback_endpoint(plan_id: int, payload: FeedbackRequest, db: Session = Depends(get_db)):
    """Submits natural feedback to update and refine an existing workout plan."""
    try:
        updated_plan = FeedbackService.submit_feedback_and_update_plan(
            db=db,
            workout_plan_id=plan_id,
            feedback_text=payload.feedback
        )
        return WorkoutPlanResponse(
            id=updated_plan.id,
            user_id=updated_plan.user_id,
            goal=updated_plan.goal,
            intensity=updated_plan.intensity,
            current_plan=WorkoutPlanContentSchema.model_validate(updated_plan.current_plan_dict),
            version=updated_plan.version,
            created_at=updated_plan.created_at,
            updated_at=updated_plan.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Plan refinement failed: {str(e)}")


@router.get("/workouts/{plan_id}/feedback", response_model=List[FeedbackResponse], tags=["Feedback"])
def get_plan_feedback_history(plan_id: int, db: Session = Depends(get_db)):
    """Retrieves historical feedback submissions for a plan."""
    return FeedbackService.get_feedback_for_plan(db, plan_id)


# ==========================================
# Nutrition Endpoints
# ==========================================

@router.post("/nutrition/tip", response_model=NutritionTipResponse, tags=["Nutrition"])
def get_nutrition_tip_endpoint(payload: NutritionTipRequest, db: Session = Depends(get_db)):
    """Generates a concise, science-backed nutrition/recovery tip tailored to fitness goal."""
    try:
        tip = NutritionService.get_tip_for_goal(db, goal=payload.goal.value, user_id=payload.user_id)
        return tip
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate nutrition tip: {str(e)}")


@router.get("/nutrition/tips", response_model=List[NutritionTipResponse], tags=["Nutrition"])
def list_nutrition_tips_endpoint(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Lists recent nutrition and recovery tips."""
    return NutritionService.get_recent_tips(db, limit=limit)



