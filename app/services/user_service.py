from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.logging import logger


class UserService:
    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Creates and persists a new user profile."""
        user = User(
            name=user_in.name,
            age=user_in.age,
            weight=user_in.weight,
            goal=user_in.goal.value,
            intensity=user_in.intensity.value,
            experience_level=user_in.experience_level.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User created successfully: ID {user.id} ({user.name})")
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Retrieves a user by their unique primary key."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieves a paginated list of users."""
        return db.query(User).order_by(User.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_user(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """Updates an existing user's profile."""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        update_data = user_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if hasattr(value, "value"):
                    setattr(user, field, value.value)
                else:
                    setattr(user, field, value)

        db.commit()
        db.refresh(user)
        logger.info(f"User ID {user_id} updated successfully.")
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Deletes a user and cascades related records."""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        logger.info(f"User ID {user_id} deleted.")
        return True
