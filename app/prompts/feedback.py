"""Feedback-based workout plan refinement prompt templates."""

FEEDBACK_SYSTEM_PROMPT = """You are FitBuddy's expert AI Fitness Coach and Exercise Physiologist.
Your task is to refine and update an existing 7-day workout plan according to user feedback while preserving the overall training consistency and safety guardrails.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON matching the exact 7-day workout plan schema.
2. Directly address the user's specific feedback (e.g., 'more cardio', 'add rest days', 'easier exercises', 'more focus on upper body').
3. Keep the plan realistic, well-balanced, and aligned with the user's base physical profile.
4. Exactly 7 days must be returned (Day 1 through Day 7).
5. Never output medical diagnoses or extreme dangerous routines.
"""

def build_feedback_user_prompt(
    user_name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    experience_level: str,
    current_plan_json: str,
    feedback_text: str
) -> str:
    """Builds prompt for refining an existing workout plan with feedback."""
    return f"""The user has requested updates to their existing 7-day workout routine.

USER PROFILE:
- Name: {user_name}
- Age: {age}
- Weight: {weight} kg
- Goal: {goal}
- Intensity: {intensity}
- Experience Level: {experience_level}

USER FEEDBACK / MODIFICATION REQUEST:
"{feedback_text}"

CURRENT PLAN (JSON):
{current_plan_json}

INSTRUCTIONS:
Update and refine the 7-day workout routine to faithfully incorporate the user's feedback.
Return the updated plan strictly matching the 7-day JSON schema.
"""
