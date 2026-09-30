import json
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import User, WorkoutPlan
from app.schemas.workout import WorkoutPlanContentSchema
from app.services.gemini_service import gemini_service
from app.core.logging import logger


class WorkoutService:
    @staticmethod
    def generate_plan_for_user(db: Session, user_id: int) -> WorkoutPlan:
        """Generates a structured 7-day plan via Gemini AI and persists it in the database."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")

        logger.info(f"Initiating AI workout generation for User #{user.id} ({user.name}, Goal: {user.goal})")

        structured_plan: WorkoutPlanContentSchema = gemini_service.generate_workout_plan(
            name=user.name,
            age=user.age,
            weight=user.weight,
            goal=user.goal,
            intensity=user.intensity,
            experience_level=user.experience_level
        )

        plan_json_str = structured_plan.model_dump_json()

        workout_plan = WorkoutPlan(
            user_id=user.id,
            goal=user.goal,
            intensity=user.intensity,
            original_plan=plan_json_str,
            current_plan=plan_json_str,
            version=1,
        )

        db.add(workout_plan)
        db.commit()
        db.refresh(workout_plan)

        logger.info(f"Workout Plan #{workout_plan.id} created and persisted for User #{user.id}")
        return workout_plan

    @staticmethod
    def get_plan_by_id(db: Session, plan_id: int) -> Optional[WorkoutPlan]:
        """Retrieves a workout plan by primary key."""
        return db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()

    @staticmethod
    def get_plans_by_user_id(db: Session, user_id: int) -> List[WorkoutPlan]:
        """Retrieves all historical workout plans generated for a given user."""
        return (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.id.desc())
            .all()
        )
