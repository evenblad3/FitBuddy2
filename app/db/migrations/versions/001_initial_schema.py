"""Initial database schema creation for FitBuddy

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-29 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('goal', sa.String(length=50), nullable=False),
        sa.Column('intensity', sa.String(length=50), nullable=False),
        sa.Column('experience_level', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Workout Plans table
    op.create_table(
        'workout_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goal', sa.String(length=50), nullable=False),
        sa.Column('intensity', sa.String(length=50), nullable=False),
        sa.Column('original_plan', sa.Text(), nullable=False),
        sa.Column('current_plan', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workout_plans_id'), 'workout_plans', ['id'], unique=False)
    op.create_index(op.f('ix_workout_plans_user_id'), 'workout_plans', ['user_id'], unique=False)

    # Plan Feedbacks table
    op.create_table(
        'plan_feedbacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workout_plan_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plan_feedbacks_id'), 'plan_feedbacks', ['id'], unique=False)
    op.create_index(op.f('ix_plan_feedbacks_user_id'), 'plan_feedbacks', ['user_id'], unique=False)
    op.create_index(op.f('ix_plan_feedbacks_workout_plan_id'), 'plan_feedbacks', ['workout_plan_id'], unique=False)

    # Nutrition Tips table
    op.create_table(
        'nutrition_tips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('goal', sa.String(length=50), nullable=False),
        sa.Column('tip', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_nutrition_tips_id'), 'nutrition_tips', ['id'], unique=False)
    op.create_index(op.f('ix_nutrition_tips_user_id'), 'nutrition_tips', ['user_id'], unique=False)

    # Admin Users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
    op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_users_username'), table_name='admin_users')
    op.drop_index(op.f('ix_admin_users_id'), table_name='admin_users')
    op.drop_table('admin_users')
    op.drop_index(op.f('ix_nutrition_tips_user_id'), table_name='nutrition_tips')
    op.drop_index(op.f('ix_nutrition_tips_id'), table_name='nutrition_tips')
    op.drop_table('nutrition_tips')
    op.drop_index(op.f('ix_plan_feedbacks_workout_plan_id'), table_name='plan_feedbacks')
    op.drop_index(op.f('ix_plan_feedbacks_user_id'), table_name='plan_feedbacks')
    op.drop_index(op.f('ix_plan_feedbacks_id'), table_name='plan_feedbacks')
    op.drop_table('plan_feedbacks')
    op.drop_index(op.f('ix_workout_plans_user_id'), table_name='workout_plans')
    op.drop_index(op.f('ix_workout_plans_id'), table_name='workout_plans')
    op.drop_table('workout_plans')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
