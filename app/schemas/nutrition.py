from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import FitnessGoalEnum


class NutritionTipRequest(BaseModel):
    user_id: Optional[int] = Field(None, description="Optional user ID to associate tip with")
    goal: FitnessGoalEnum = Field(..., description="Target fitness goal")


class NutritionTipResponse(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    goal: str
    tip: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
