from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=3, max_length=1000, description="User's feedback or modification instructions")

    @field_validator("feedback")
    @classmethod
    def sanitize_feedback(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Feedback cannot be empty or solely whitespace.")
        return v


class FeedbackResponse(BaseModel):
    id: int
    workout_plan_id: int
    user_id: int
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
