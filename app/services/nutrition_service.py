from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import NutritionTip, User
from app.schemas.nutrition import NutritionTipRequest, NutritionTipResponse
from app.services.gemini_service import gemini_service
from app.core.logging import logger


class NutritionService:
    @staticmethod
    def get_tip_for_goal(db: Session, goal: str, user_id: Optional[int] = None) -> NutritionTip:
        """Generates a goal-tailored nutrition/recovery tip using Gemini AI and stores it in DB."""
        user_name = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user_name = user.name

        logger.info(f"Generating nutrition guidance for goal: '{goal}' (User ID: {user_id})")
        tip_content = gemini_service.generate_nutrition_tip(goal=goal, user_name=user_name)

        nutrition_tip = NutritionTip(
            user_id=user_id,
            goal=goal,
            tip=tip_content
        )
        db.add(nutrition_tip)
        db.commit()
        db.refresh(nutrition_tip)
        logger.info(f"Nutrition Tip #{nutrition_tip.id} saved for goal '{goal}'.")
        return nutrition_tip

    @staticmethod
    def get_recent_tips(db: Session, user_id: Optional[int] = None, limit: int = 20) -> List[NutritionTip]:
        """Retrieves recent tips optionally filtered by user."""
        query = db.query(NutritionTip)
        if user_id:
            query = query.filter(NutritionTip.user_id == user_id)
        return query.order_by(NutritionTip.id.desc()).limit(limit).all()
