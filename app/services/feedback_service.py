from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import WorkoutPlan, PlanFeedback, User
from app.schemas.workout import WorkoutPlanContentSchema
from app.services.gemini_service import gemini_service
from app.core.logging import logger


class FeedbackService:
    @staticmethod
    def submit_feedback_and_update_plan(
        db: Session,
        workout_plan_id: int,
        feedback_text: str
    ) -> WorkoutPlan:
        """Processes user feedback, saves the feedback log, refines plan via Gemini, and increments version."""
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == workout_plan_id).first()
        if not plan:
            raise ValueError(f"Workout plan #{workout_plan_id} not found.")

        user = db.query(User).filter(User.id == plan.user_id).first()
        if not user:
            raise ValueError(f"User for plan #{workout_plan_id} not found.")

        feedback_clean = feedback_text.strip()
        if not feedback_clean:
            raise ValueError("Feedback cannot be empty.")

        # 1. Record feedback entry
        feedback_entry = PlanFeedback(
            workout_plan_id=plan.id,
            user_id=user.id,
            feedback=feedback_clean
        )
        db.add(feedback_entry)

        # 2. Call AI refinement engine
        logger.info(f"Refining Plan #{plan.id} (Version {plan.version}) with feedback: '{feedback_clean[:50]}'")
        refined_plan_schema: WorkoutPlanContentSchema = gemini_service.refine_workout_plan(
            name=user.name,
            age=user.age,
            weight=user.weight,
            goal=user.goal,
            intensity=user.intensity,
            experience_level=user.experience_level,
            current_plan_dict=plan.current_plan_dict,
            feedback_text=feedback_clean
        )

        # 3. Update current plan while preserving original_plan & increment version
        plan.current_plan = refined_plan_schema.model_dump_json()
        plan.version += 1

        db.commit()
        db.refresh(plan)

        logger.info(f"Plan #{plan.id} updated to Version {plan.version} successfully.")
        return plan

    @staticmethod
    def get_feedback_for_plan(db: Session, workout_plan_id: int) -> List[PlanFeedback]:
        """Retrieves all feedback records submitted for a workout plan."""
        return (
            db.query(PlanFeedback)
            .filter(PlanFeedback.workout_plan_id == workout_plan_id)
            .order_by(PlanFeedback.id.desc())
            .all()
        )
