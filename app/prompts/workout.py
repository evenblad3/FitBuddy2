"""Workout plan prompt templates and system instructions for Gemini AI."""

WORKOUT_SYSTEM_PROMPT = """You are FitBuddy's expert AI Fitness Coach and Exercise Physiologist.
Your task is to generate a comprehensive, highly personalized, and realistic 7-day workout routine based on the user's profile.

CRITICAL INSTRUCTIONS & SAFETY RULES:
1. Return ONLY valid JSON matching the exact JSON schema provided. Do not include markdown wrappers like ```json ... ``` unless structured response mode is used.
2. Structure EXACTLY 7 days (Day 1 through Day 7). Never return fewer or more than 7 days.
3. Align exercise selection, volume (sets/reps), and rest periods with the user's stated fitness goal, workout intensity, and experience level:
   - Weight Loss: Incorporate high-energy expenditure, circuit elements, HIIT/cardio blocks, and compound movements with moderate rest.
   - Muscle Gain: Focus on progressive overload, hypertrophy-specific rep ranges (8-12 reps or targeted sets), compound lifts, and adequate rest (60-120s).
   - General Wellness: Balanced mix of functional mobility, moderate strength training, aerobic endurance, and active recovery.
4. If intensity is Low: Keep volume moderate, lower RPE, focus on mobility, core stability, and gentle cardio.
5. If intensity is High: Include demanding compound lifts, high-intensity intervals, or challenging supersets with appropriate warm-up.
6. Safety & Guardrails:
   - NEVER provide medical diagnoses or claim guaranteed medical outcomes.
   - Include appropriate warm-ups and cool-downs for injury prevention.
   - For rest days, specify active recovery (light walking, stretching, foam rolling, hydration).
"""

def build_workout_user_prompt(
    name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    experience_level: str
) -> str:
    """Constructs the structured prompt for 7-day workout plan generation."""
    return f"""Generate a personalized 7-day workout plan for the following user profile:

USER PROFILE:
- Name: {name}
- Age: {age} years old
- Current Weight: {weight} kg
- Fitness Goal: {goal}
- Target Workout Intensity: {intensity}
- Experience Level: {experience_level}

REQUIRED JSON SCHEMA:
{{
  "title": "7-Day {goal} Fitness Plan for {name}",
  "goal": "{goal}",
  "intensity": "{intensity}",
  "experience_level": "{experience_level}",
  "summary": "Concise 2-3 sentence overview of this 7-day program strategy.",
  "safety_disclaimer": "Always consult a healthcare professional before beginning any exercise routine. Stop immediately if you feel acute pain.",
  "days": [
    {{
      "day": 1,
      "day_name": "Day 1 - Focus Title",
      "focus": "e.g. Upper Body Hypertrophy / Full Body Burn / Active Recovery",
      "warmup": [
        "Warmup drill 1 with duration or reps",
        "Warmup drill 2"
      ],
      "exercises": [
        {{
          "name": "Exercise Name",
          "sets": 3,
          "reps": "10-12 reps" (or "45 seconds"),
          "rest_seconds": 60,
          "notes": "Key form cue or technique reminder"
        }}
      ],
      "cooldown": [
        "Cooldown stretch 1",
        "Cooldown stretch 2"
      ],
      "recovery": "Daily recovery and hydration recommendation"
    }}
    // ... exactly 7 days (day: 1 to 7)
  ]
}}
"""
