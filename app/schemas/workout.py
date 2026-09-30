from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import FitnessGoalEnum, IntensityEnum, ExperienceLevelEnum


class ExerciseSchema(BaseModel):
    name: str = Field(..., description="Name of the exercise")
    sets: Optional[int] = Field(None, ge=1, le=20, description="Number of sets")
    reps: Optional[str] = Field(None, description="Reps count (e.g., '10-12') or duration (e.g., '30s')")
    rest_seconds: Optional[int] = Field(None, ge=0, le=600, description="Rest time between sets in seconds")
    notes: Optional[str] = Field(None, description="Form tips or modifications")


class DayPlanSchema(BaseModel):
    day: int = Field(..., ge=1, le=7, description="Day number (1 to 7)")
    day_name: Optional[str] = Field(None, description="e.g. Day 1 - Monday")
    focus: str = Field(..., description="Workout focus or rest day title")
    warmup: List[str] = Field(default_factory=list, description="Warm-up drills")
    exercises: List[ExerciseSchema] = Field(default_factory=list, description="Target exercises")
    cooldown: List[str] = Field(default_factory=list, description="Cool-down stretches")
    recovery: Optional[str] = Field(None, description="Recovery or hydration tip for this day")


class WorkoutPlanContentSchema(BaseModel):
    title: str = Field(default="7-Day Personalized Workout Plan")
    goal: FitnessGoalEnum
    intensity: IntensityEnum
    experience_level: ExperienceLevelEnum = ExperienceLevelEnum.BEGINNER
    summary: Optional[str] = Field(None, description="Executive overview of the 7-day routine")
    safety_disclaimer: str = Field(
        default="Always consult a physician before beginning any exercise program. Listen to your body and discontinue if you experience sharp pain."
    )
    days: List[DayPlanSchema] = Field(..., min_length=7, max_length=7, description="Structured 7 days of training")


class WorkoutGenerateRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user to generate the plan for")


class WorkoutPlanResponse(BaseModel):
    id: int
    user_id: int
    goal: str
    intensity: str
    current_plan: WorkoutPlanContentSchema
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
