"""Nutrition and recovery prompt templates."""

NUTRITION_SYSTEM_PROMPT = """You are FitBuddy's AI Nutrition and Wellness Advisor.
Your job is to provide concise, practical, and science-informed nutrition and recovery tips.

SAFETY & COMPLIANCE:
- Do NOT prescribe medical diets or claim to cure diseases.
- Keep tips actionable, balanced, and under 3 concise sentences.
- Emphasize hydration, whole foods, protein distribution, and quality sleep.
"""

def build_nutrition_tip_prompt(goal: str, user_name: str = None) -> str:
    """Builds prompt for requesting goal-based nutrition or recovery guidance."""
    user_context = f" for {user_name}" if user_name else ""
    return f"""Provide a concise, practical nutrition and recovery tip{user_context} focusing on the fitness goal: '{goal}'.

Include:
1. One key dietary habit (e.g., protein timing, hydration, or caloric awareness).
2. One key recovery practice (e.g., sleep hygiene or post-workout refueling).
Keep the response within 2-3 sentences max.
"""
