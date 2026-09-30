from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    goal = Column(String(50), nullable=False)  # Weight Loss, Muscle Gain, General Wellness
    intensity = Column(String(50), nullable=False)  # Low, Medium, High
    experience_level = Column(String(50), nullable=False, default="Beginner")  # Beginner, Intermediate, Advanced
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan", order_by="desc(WorkoutPlan.id)")
    feedbacks = relationship("PlanFeedback", back_populates="user", cascade="all, delete-orphan")
    nutrition_tips = relationship("NutritionTip", back_populates="user", cascade="all, delete-orphan")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal = Column(String(50), nullable=False)
    intensity = Column(String(50), nullable=False)
    original_plan = Column(Text, nullable=False)  # JSON string of the structured plan
    current_plan = Column(Text, nullable=False)   # JSON string of current version
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="workout_plans")
    feedbacks = relationship("PlanFeedback", back_populates="workout_plan", cascade="all, delete-orphan", order_by="PlanFeedback.id")

    @property
    def current_plan_dict(self):
        try:
            return json.loads(self.current_plan)
        except Exception:
            return {}

    @property
    def original_plan_dict(self):
        try:
            return json.loads(self.original_plan)
        except Exception:
            return {}


class PlanFeedback(Base):
    __tablename__ = "plan_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    workout_plan_id = Column(Integer, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workout_plan = relationship("WorkoutPlan", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")


class NutritionTip(Base):
    __tablename__ = "nutrition_tips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    goal = Column(String(50), nullable=False)
    tip = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="nutrition_tips")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
