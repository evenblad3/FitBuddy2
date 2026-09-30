from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FitnessGoalEnum(str, Enum):
    WEIGHT_LOSS = "Weight Loss"
    MUSCLE_GAIN = "Muscle Gain"
    GENERAL_WELLNESS = "General Wellness"


class IntensityEnum(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ExperienceLevelEnum(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User's full or first name")
    age: int = Field(..., ge=12, le=120, description="User's age in years")
    weight: float = Field(..., ge=20.0, le=400.0, description="User's weight in kilograms")
    goal: FitnessGoalEnum = Field(..., description="Target fitness goal")
    intensity: IntensityEnum = Field(..., description="Preferred workout intensity")
    experience_level: ExperienceLevelEnum = Field(default=ExperienceLevelEnum.BEGINNER, description="Fitness experience level")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank or just whitespace.")
        return v


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=12, le=120)
    weight: Optional[float] = Field(None, ge=20.0, le=400.0)
    goal: Optional[FitnessGoalEnum] = None
    intensity: Optional[IntensityEnum] = None
    experience_level: Optional[ExperienceLevelEnum] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
