from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import AdminUser, User, WorkoutPlan, PlanFeedback, NutritionTip
from app.core.security import hash_password, verify_password
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class AdminService:
    @staticmethod
    def ensure_default_admin(db: Session) -> None:
        """Seeds the default admin user into the database if none exists."""
        admin_count = db.query(AdminUser).count()
        if admin_count == 0:
            default_username = settings.ADMIN_USERNAME
            default_password = settings.ADMIN_PASSWORD
            hashed = hash_password(default_password)
            admin = AdminUser(username=default_username, password_hash=hashed)
            db.add(admin)
            db.commit()
            logger.info(f"Default admin user '{default_username}' created successfully.")

    @staticmethod
    def authenticate_admin(db: Session, username: str, password: str) -> Optional[AdminUser]:
        """Validates admin credentials."""
        # Ensure default admin exists
        AdminService.ensure_default_admin(db)
        admin = db.query(AdminUser).filter(AdminUser.username == username.strip()).first()
        if not admin:
            return None
        if verify_password(password, admin.password_hash):
            return admin
        return None

    @staticmethod
    def get_system_metrics(db: Session) -> Dict[str, Any]:
        """Calculates aggregated metrics for admin dashboard."""
        total_users = db.query(User).count()
        total_plans = db.query(WorkoutPlan).count()
        total_feedback = db.query(PlanFeedback).count()
        total_tips = db.query(NutritionTip).count()

        # Goal distribution
        goal_stats = (
            db.query(User.goal, func.count(User.id))
            .group_by(User.goal)
            .all()
        )
        goal_distribution = {goal: count for goal, count in goal_stats}

        # Intensity distribution
        intensity_stats = (
            db.query(User.intensity, func.count(User.id))
            .group_by(User.intensity)
            .all()
        )
        intensity_distribution = {intensity: count for intensity, count in intensity_stats}

        return {
            "total_users": total_users,
            "total_plans": total_plans,
            "total_feedback": total_feedback,
            "total_tips": total_tips,
            "goal_distribution": goal_distribution,
            "intensity_distribution": intensity_distribution,
        }

    @staticmethod
    def get_user_with_full_details(db: Session, user_id: int) -> Optional[User]:
        """Retrieves user with their plans, feedbacks, and nutrition tips eager-loaded."""
        return db.query(User).filter(User.id == user_id).first()
