import json
import re
from typing import Optional, Dict, Any
from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.workout import WorkoutPlanContentSchema, DayPlanSchema, ExerciseSchema
from app.schemas.user import FitnessGoalEnum, IntensityEnum, ExperienceLevelEnum
from app.prompts.workout import WORKOUT_SYSTEM_PROMPT, build_workout_user_prompt
from app.prompts.feedback import FEEDBACK_SYSTEM_PROMPT, build_feedback_user_prompt
from app.prompts.nutrition import NUTRITION_SYSTEM_PROMPT, build_nutrition_tip_prompt

# Try importing google-genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiService:
    def __init__(self):
        self._client = None

    def get_client(self):
        """Lazily initializes and retrieves Google GenAI client with stripped API key."""
        settings = get_settings()
        api_key = (settings.GEMINI_API_KEY or "").strip()
        if not api_key:
            return None
        if not GENAI_AVAILABLE:
            logger.warning("google-genai SDK is not installed.")
            return None
        if not self._client:
            try:
                self._client = genai.Client(api_key=api_key)
                logger.info("Google GenAI client initialized with configured API key.")
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
                return None
        return self._client

    def _clean_json_response(self, text: str) -> str:
        """Extracts and cleans raw JSON string from AI model output."""
        cleaned = text.strip()
        # Strip markdown ```json ... ``` codeblocks if present
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
        return cleaned

    def generate_workout_plan(
        self,
        name: str,
        age: int,
        weight: float,
        goal: str,
        intensity: str,
        experience_level: str
    ) -> WorkoutPlanContentSchema:
        """Generates a structured 7-day workout plan using Gemini or robust fallback."""
        client = self.get_client()
        settings = get_settings()
        if not client:
            logger.info(f"Using fallback generator for {name} ({goal}, {intensity}).")
            return self._build_deterministic_plan(name, age, weight, goal, intensity, experience_level)

        user_prompt = build_workout_user_prompt(name, age, weight, goal, intensity, experience_level)

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_WORKOUT_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=WORKOUT_SYSTEM_PROMPT,
                    temperature=0.4,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text or ""
            cleaned_json = self._clean_json_response(raw_text)
            parsed_data = json.loads(cleaned_json)
            plan = WorkoutPlanContentSchema.model_validate(parsed_data)
            logger.info(f"Gemini successfully generated 7-day plan for {name}.")
            return plan

        except Exception as e:
            logger.error(f"Gemini API error during workout generation: {e}. Falling back to default plan generator.", exc_info=False)
            return self._build_deterministic_plan(name, age, weight, goal, intensity, experience_level)

    def refine_workout_plan(
        self,
        name: str,
        age: int,
        weight: float,
        goal: str,
        intensity: str,
        experience_level: str,
        current_plan_dict: Dict[str, Any],
        feedback_text: str
    ) -> WorkoutPlanContentSchema:
        """Updates an existing workout plan with user feedback via Gemini or rule-based updater."""
        client = self.get_client()
        settings = get_settings()
        if not client:
            return self._refine_deterministic_plan(current_plan_dict, feedback_text, goal, intensity)

        current_plan_json = json.dumps(current_plan_dict)
        user_prompt = build_feedback_user_prompt(
            user_name=name,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
            experience_level=experience_level,
            current_plan_json=current_plan_json,
            feedback_text=feedback_text
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_WORKOUT_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=FEEDBACK_SYSTEM_PROMPT,
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text or ""
            cleaned_json = self._clean_json_response(raw_text)
            parsed_data = json.loads(cleaned_json)
            updated_plan = WorkoutPlanContentSchema.model_validate(parsed_data)
            logger.info(f"Gemini successfully refined plan for {name} with feedback: '{feedback_text[:40]}...'")
            return updated_plan

        except Exception as e:
            logger.error(f"Gemini API error during plan refinement: {e}. Applying fallback modification.", exc_info=False)
            return self._refine_deterministic_plan(current_plan_dict, feedback_text, goal, intensity)

    def generate_nutrition_tip(self, goal: str, user_name: Optional[str] = None) -> str:
        """Generates a concise nutrition or recovery tip."""
        client = self.get_client()
        settings = get_settings()
        if not client:
            return self._get_fallback_nutrition_tip(goal)

        prompt = build_nutrition_tip_prompt(goal, user_name)

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_FAST_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=NUTRITION_SYSTEM_PROMPT,
                    temperature=0.5,
                    max_output_tokens=150
                )
            )
            tip_text = (response.text or "").strip()
            if tip_text:
                return tip_text
            return self._get_fallback_nutrition_tip(goal)
        except Exception as e:
            logger.warning(f"Gemini API error during nutrition tip generation: {e}")
            return self._get_fallback_nutrition_tip(goal)

    # -------------------------------------------------------------
    # High-Fidelity Fallback Logic for Offline/Mock Development
    # -------------------------------------------------------------
    def _build_deterministic_plan(
        self,
        name: str,
        age: int,
        weight: float,
        goal: str,
        intensity: str,
        experience_level: str
    ) -> WorkoutPlanContentSchema:
        """Constructs an expert-verified, structured 7-day workout plan based on user goals."""
        goal_enum = FitnessGoalEnum(goal) if goal in [g.value for g in FitnessGoalEnum] else FitnessGoalEnum.GENERAL_WELLNESS
        intensity_enum = IntensityEnum(intensity) if intensity in [i.value for i in IntensityEnum] else IntensityEnum.MEDIUM
        exp_enum = ExperienceLevelEnum(experience_level) if experience_level in [e.value for e in ExperienceLevelEnum] else ExperienceLevelEnum.BEGINNER

        if goal_enum == FitnessGoalEnum.WEIGHT_LOSS:
            days = [
                DayPlanSchema(
                    day=1,
                    day_name="Day 1 - High Energy Full Body Burn",
                    focus="Full Body Metabolic Conditioning",
                    warmup=["5 min Light Jog / Jumping Jacks", "Arm Circles & Torso Twists", "10 Bodyweight Squats"],
                    exercises=[
                        ExerciseSchema(name="Goblet Squats", sets=4, reps="15 reps", rest_seconds=45, notes="Keep chest upright, drive through heels"),
                        ExerciseSchema(name="Dumbbell Push Press", sets=3, reps="12 reps", rest_seconds=45, notes="Use slight leg dip to generate upward momentum"),
                        ExerciseSchema(name="Kettlebell / Dumbbell Swings", sets=4, reps="20 reps", rest_seconds=60, notes="Hinge at hips, squeeze glutes at top"),
                        ExerciseSchema(name="Plank Hold", sets=3, reps="45 seconds", rest_seconds=30, notes="Maintain neutral spine and engage core"),
                    ],
                    cooldown=["Hamstring Stretches (60s)", "Child's Pose (60s)", "Deep Diaphragmatic Breathing"],
                    recovery="Drink at least 500ml water immediately post-workout and maintain a high-protein deficit."
                ),
                DayPlanSchema(
                    day=2,
                    day_name="Day 2 - Cardio Intervals & Core",
                    focus="Cardiovascular Endurance & Midsection Stability",
                    warmup=["3 min Dynamic Walking High Knees", "Cat-Cow Stretch (10 reps)", "Inchworms (5 reps)"],
                    exercises=[
                        ExerciseSchema(name="Incline Treadmill Walk / Brisk Walking", sets=1, reps="25 mins", rest_seconds=0, notes="Maintain steady heart rate zone 2/3"),
                        ExerciseSchema(name="Bicycle Crunches", sets=3, reps="20 reps total", rest_seconds=30, notes="Slow and controlled elbow-to-knee contact"),
                        ExerciseSchema(name="Mountain Climbers", sets=3, reps="30 seconds", rest_seconds=45, notes="Keep shoulders directly stacked over wrists"),
                    ],
                    cooldown=["Seated Forward Fold", "Cobra Stretch for abs", "Shoulder stretch"],
                    recovery="Prioritize 8 hours of sleep for central nervous system restoration."
                ),
                DayPlanSchema(
                    day=3,
                    day_name="Day 3 - Lower Body Tone & Glute Activation",
                    focus="Lower Body Strength & Caloric Burn",
                    warmup=["5 min Stationary Bike", "Leg Swings (Front/Back & Lateral)", "Glute Bridges (15 reps)"],
                    exercises=[
                        ExerciseSchema(name="Walking Dumbbell Lunges", sets=3, reps="12 steps/leg", rest_seconds=60, notes="Maintain upright posture and 90-degree knee bend"),
                        ExerciseSchema(name="Romanian Deadlifts (Dumbbells)", sets=4, reps="12 reps", rest_seconds=60, notes="Hinge hips back with a soft knee bend"),
                        ExerciseSchema(name="Step-Ups on Bench", sets=3, reps="10 reps/leg", rest_seconds=45, notes="Drive through the lead foot"),
                        ExerciseSchema(name="Calf Raises", sets=3, reps="20 reps", rest_seconds=30, notes="Hold peak contraction for 1 second"),
                    ],
                    cooldown=["Quad Stretches", "Pigeon Pose (45s each leg)", "Hydration check"],
                    recovery="Consume a light potassium-rich snack (e.g., banana) to prevent muscle cramping."
                ),
                DayPlanSchema(
                    day=4,
                    day_name="Day 4 - Active Recovery & Mobility",
                    focus="Active Rest & Joint Decompression",
                    warmup=["5 min Gentle Walking"],
                    exercises=[
                        ExerciseSchema(name="Outdoor Walking / Easy Stroll", sets=1, reps="30 mins", rest_seconds=0, notes="Low-intensity aerobic recovery"),
                        ExerciseSchema(name="Full Body Foam Rolling", sets=1, reps="15 mins", rest_seconds=0, notes="Focus on quads, IT bands, and upper back"),
                    ],
                    cooldown=["Full body relaxation stretches", "Light hydration with electrolytes"],
                    recovery="Take a warm Epsom salt bath or contrast shower to enhance tissue repair."
                ),
                DayPlanSchema(
                    day=5,
                    day_name="Day 5 - Upper Body & HIIT Finish",
                    focus="Upper Body Tone & High-Intensity Burst",
                    warmup=["Band Pull-Aparts (15 reps)", "Arm circles", "Wall Push-Ups (10 reps)"],
                    exercises=[
                        ExerciseSchema(name="Dumbbell Rows", sets=4, reps="12 reps", rest_seconds=45, notes="Pull elbows back towards hips"),
                        ExerciseSchema(name="Push-Ups (or Incline Push-Ups)", sets=3, reps="10-12 reps", rest_seconds=45, notes="Keep body in a rigid straight plank"),
                        ExerciseSchema(name="Lateral Raises", sets=3, reps="15 reps", rest_seconds=30, notes="Lead with elbows, avoid swinging weights"),
                        ExerciseSchema(name="Burpees / Elevated Sprawls", sets=4, reps="30 seconds on / 30s off", rest_seconds=30, notes="Finish with max aerobic effort"),
                    ],
                    cooldown=["Chest Doorway Stretch", "Cross-body Shoulder Stretch", "Deep breathing"],
                    recovery="Refuel with a lean protein shake or grilled chicken salad within 60 minutes."
                ),
                DayPlanSchema(
                    day=6,
                    day_name="Day 6 - Functional Core & Agility",
                    focus="Total Body Core, Balance & Coordination",
                    warmup=["Shadow Boxing / High Knees (3 mins)", "Hip Openers"],
                    exercises=[
                        ExerciseSchema(name="Russian Twists (Bodyweight or Light DB)", sets=3, reps="20 reps", rest_seconds=30, notes="Rotate torso fully with knees bent"),
                        ExerciseSchema(name="Side Plank Holds", sets=3, reps="30 seconds/side", rest_seconds=30, notes="Keep hip lifted high off the ground"),
                        ExerciseSchema(name="Jump Rope / Air Skips", sets=4, reps="1 minute", rest_seconds=45, notes="Land softly on the balls of your feet"),
                    ],
                    cooldown=["Butterfly stretch", "Cat-Cow", "Lower back spinal twists"],
                    recovery="Keep hydrated with at least 2.5 liters of clean water throughout the day."
                ),
                DayPlanSchema(
                    day=7,
                    day_name="Day 7 - Complete Rest & Weekly Reset",
                    focus="Restoration, Nutrition Prep & Mindset",
                    warmup=[],
                    exercises=[
                        ExerciseSchema(name="Light Leisure Walk / Gentle Yoga", sets=1, reps="20 mins", rest_seconds=0, notes="Completely optional and relaxed"),
                    ],
                    cooldown=["Gentle full body static stretching"],
                    recovery="Plan your nutrient-dense meals for the upcoming week and log your progress."
                )
            ]
        elif goal_enum == FitnessGoalEnum.MUSCLE_GAIN:
            days = [
                DayPlanSchema(
                    day=1,
                    day_name="Day 1 - Chest & Triceps Hypertrophy",
                    focus="Upper Body Push Strength",
                    warmup=["5 min Row Ergometer", "Arm Circles & Band Dislocates", "Light Push-Ups (10 reps)"],
                    exercises=[
                        ExerciseSchema(name="Dumbbell / Barbell Bench Press", sets=4, reps="8-10 reps", rest_seconds=90, notes="Control 2-second eccentric descent, explosive press"),
                        ExerciseSchema(name="Incline Dumbbell Press", sets=3, reps="10-12 reps", rest_seconds=75, notes="Target upper clavicular head of pectorals"),
                        ExerciseSchema(name="Dumbbell Chest Flyes", sets=3, reps="12-15 reps", rest_seconds=60, notes="Focus on deep chest stretch without joint strain"),
                        ExerciseSchema(name="Tricep Rope Pushdowns / Overhead Extensions", sets=3, reps="12-15 reps", rest_seconds=60, notes="Lock out triceps at bottom"),
                    ],
                    cooldown=["Chest Doorway Stretch", "Overhead Tricep Stretch"],
                    recovery="Consume 30-40g whey protein or complete protein source with complex carbohydrates."
                ),
                DayPlanSchema(
                    day=2,
                    day_name="Day 2 - Back & Biceps Hypertrophy",
                    focus="Upper Body Pull Volume",
                    warmup=["5 min Elliptical", "Lat Band Pulls", "Dead hangs (2 x 20s)"],
                    exercises=[
                        ExerciseSchema(name="Lat Pulldowns / Pull-Ups", sets=4, reps="8-10 reps", rest_seconds=90, notes="Drive elbows down toward back pockets"),
                        ExerciseSchema(name="Bent-Over Barbell or Dumbbell Rows", sets=4, reps="8-10 reps", rest_seconds=90, notes="Maintain flat back and neutral neck"),
                        ExerciseSchema(name="Seated Cable / Resistance Band Rows", sets=3, reps="12 reps", rest_seconds=60, notes="Squeeze shoulder blades together for 1s"),
                        ExerciseSchema(name="Incline Dumbbell Bicep Curls", sets=3, reps="10-12 reps", rest_seconds=60, notes="Keep upper arm stationary"),
                    ],
                    cooldown=["Lat stretch", "Bicep wall stretch", "Spinal decompression"],
                    recovery="Ensure consistent creatine and hydration intake."
                ),
                DayPlanSchema(
                    day=3,
                    day_name="Day 3 - Quadriceps, Hamstrings & Calves",
                    focus="Lower Body Squat & Hinge Power",
                    warmup=["5 min Stationary Bike", "Bodyweight Squats (15 reps)", "Hip Flexor Dynamic Lunge"],
                    exercises=[
                        ExerciseSchema(name="Barbell / Dumbbell Back Squats", sets=4, reps="8-10 reps", rest_seconds=120, notes="Break parallel with knee tracking over toes"),
                        ExerciseSchema(name="Romanian Deadlifts", sets=4, reps="10 reps", rest_seconds=90, notes="Feel maximum hamstring stretch at bottom"),
                        ExerciseSchema(name="Leg Press / Bulgarian Split Squats", sets=3, reps="10 reps/leg", rest_seconds=75, notes="Keep lead foot planted flat"),
                        ExerciseSchema(name="Standing Calf Raises", sets=4, reps="15 reps", rest_seconds=45, notes="Pause 2 seconds at full peak stretch"),
                    ],
                    cooldown=["Hamstring stretch", "Quad foam roll", "Pigeon pose"],
                    recovery="Prioritize post-workout meal with sweet potato / rice and lean steak or chicken."
                ),
                DayPlanSchema(
                    day=4,
                    day_name="Day 4 - Active Recovery & Structural Restoration",
                    focus="Deload, Flexibility & Core Stability",
                    warmup=["Gentle Mobility Drills"],
                    exercises=[
                        ExerciseSchema(name="Hanging Leg Raises / Captain's Chair", sets=3, reps="12 reps", rest_seconds=45, notes="Avoid swinging, initiate with hip flexors and lower abs"),
                        ExerciseSchema(name="Ab Wheel Rollouts or Plank Holds", sets=3, reps="10 reps / 45s", rest_seconds=45, notes="Maintain strong pelvic tilt"),
                        ExerciseSchema(name="Light 20-min Walk", sets=1, reps="20 mins", rest_seconds=0, notes="Promote nutrient delivery to recovering muscle tissues"),
                    ],
                    cooldown=["Full body yoga flow"],
                    recovery="Get 8-9 hours of restful sleep."
                ),
                DayPlanSchema(
                    day=5,
                    day_name="Day 5 - Shoulders & Arms",
                    focus="Deltoid Sculpting & Arm Density",
                    warmup=["Arm circles", "Light DB Shoulder Press (10 reps)", "Lateral raise prep"],
                    exercises=[
                        ExerciseSchema(name="Overhead Dumbbell / Barbell Press", sets=4, reps="8-10 reps", rest_seconds=90, notes="Keep core tight and glutes squeezed"),
                        ExerciseSchema(name="Dumbbell Lateral Raises", sets=4, reps="12-15 reps", rest_seconds=45, notes="Slight forward lean to bias lateral deltoid"),
                        ExerciseSchema(name="Face Pulls (Cable / Band)", sets=3, reps="15 reps", rest_seconds=45, notes="Target rear delts and external rotators"),
                        ExerciseSchema(name="Hammer Curls & Skull Crushers Superset", sets=3, reps="10-12 reps each", rest_seconds=60, notes="Solid mind-muscle connection"),
                    ],
                    cooldown=["Shoulder cross-arm stretch", "Tricep overhead stretch"],
                    recovery="Hydrate and replenish glycogen stores."
                ),
                DayPlanSchema(
                    day=6,
                    day_name="Day 6 - Lower Body Posterior & Core",
                    focus="Glute, Hamstring & Trap Work",
                    warmup=["Glute bridges", "Monster walks with resistance band"],
                    exercises=[
                        ExerciseSchema(name="Hip Thrusts / Glute Bridges (Barbell/DB)", sets=4, reps="10-12 reps", rest_seconds=90, notes="Tuck chin, full hip extension at top"),
                        ExerciseSchema(name="Lying or Seated Hamstring Curls", sets=3, reps="12 reps", rest_seconds=60, notes="Control negative descent"),
                        ExerciseSchema(name="Farmer's Carries", sets=3, reps="40 meters", rest_seconds=60, notes="Grip heavy dumbbells, walk tall with neutral posture"),
                    ],
                    cooldown=["Glute stretch", "Seated hamstring stretch"],
                    recovery="Eat a balanced surplus of protein and carbohydrates for tissue synthesis."
                ),
                DayPlanSchema(
                    day=7,
                    day_name="Day 7 - Total Body Rest",
                    focus="Deep Recovery & Systemic Rebuilding",
                    warmup=[],
                    exercises=[
                        ExerciseSchema(name="Complete Rest / Gentle 15-min Stroll", sets=1, reps="15 mins", rest_seconds=0, notes="Recharge for the upcoming microcycle"),
                    ],
                    cooldown=["Light static stretching"],
                    recovery="Hydrate well and prepare for week progression."
                )
            ]
        else: # General Wellness
            days = [
                DayPlanSchema(
                    day=1,
                    day_name="Day 1 - Total Body Foundation",
                    focus="Full Body Functional Strength",
                    warmup=["5 min Walk / Easy Cycling", "Shoulder Rolls & Torso Rotations", "Bodyweight Squats (10 reps)"],
                    exercises=[
                        ExerciseSchema(name="Bodyweight / Goblet Squats", sets=3, reps="10-12 reps", rest_seconds=60, notes="Focus on smooth depth and knee alignment"),
                        ExerciseSchema(name="Incline Push-Ups / Standard Push-Ups", sets=3, reps="10 reps", rest_seconds=60, notes="Keep spine neutral and elbows at 45 degrees"),
                        ExerciseSchema(name="Dumbbell Rows / Resistance Band Pulls", sets=3, reps="12 reps", rest_seconds=60, notes="Focus on posture and scapular retraction"),
                        ExerciseSchema(name="Plank Hold", sets=3, reps="30-40 seconds", rest_seconds=45, notes="Engage glutes and core"),
                    ],
                    cooldown=["Cat-Cow Stretch (10 reps)", "Hamstring Stretch (45s/side)", "Deep breathing"],
                    recovery="Drink plenty of water and enjoy a balanced, colorful whole-food meal."
                ),
                DayPlanSchema(
                    day=2,
                    day_name="Day 2 - Aerobic Conditioning & Walking",
                    focus="Cardiovascular Health & Joint Low-Impact",
                    warmup=["3 min Gentle Dynamic Arm and Leg Swings"],
                    exercises=[
                        ExerciseSchema(name="Brisk Outdoor Walk or Stationary Cycling", sets=1, reps="30 mins", rest_seconds=0, notes="Breathe steadily, maintain conversational pace"),
                        ExerciseSchema(name="Bird-Dog Exercise", sets=3, reps="10 reps/side", rest_seconds=30, notes="Extend opposite arm and leg while bracing core"),
                    ],
                    cooldown=["Calf Stretch against wall", "Quad Stretch"],
                    recovery="Aim for 7.5+ hours of uninterrupted sleep."
                ),
                DayPlanSchema(
                    day=3,
                    day_name="Day 3 - Mobility & Spine Health",
                    focus="Joint Flexibility, Posture & Movement Quality",
                    warmup=["Child's Pose to Cobra Flow (5 reps)"],
                    exercises=[
                        ExerciseSchema(name="Thoracic Spine Rotations (Open Books)", sets=2, reps="10 reps/side", rest_seconds=30, notes="Breathe out as you open chest"),
                        ExerciseSchema(name="World's Greatest Stretch", sets=2, reps="5 reps/side", rest_seconds=30, notes="Lunge forward with elbow inside front foot"),
                        ExerciseSchema(name="Glute Bridge Holds", sets=3, reps="12 reps (2s hold)", rest_seconds=45, notes="Engage glutes, protect lower back"),
                    ],
                    cooldown=["Pigeon Pose / Figure-4 Stretch", "Relaxation breathing"],
                    recovery="Stay hydrated with clean water and herbal tea."
                ),
                DayPlanSchema(
                    day=4,
                    day_name="Day 4 - Lower Body Stability & Balance",
                    focus="Lower Body Endurance & Single-Leg Balance",
                    warmup=["5 min Easy March in place", "Ankle Rotations"],
                    exercises=[
                        ExerciseSchema(name="Reverse Lunges (Bodyweight or Light DB)", sets=3, reps="10 reps/leg", rest_seconds=60, notes="Step backward, land lightly on ball of rear foot"),
                        ExerciseSchema(name="Step-Ups on Low Platform", sets=3, reps="10 reps/leg", rest_seconds=45, notes="Controlled step down"),
                        ExerciseSchema(name="Standing Calf & Toe Raises", sets=3, reps="15 reps", rest_seconds=30, notes="Enhance ankle stability and circulation"),
                    ],
                    cooldown=["Seated Hamstring Stretch", "Butterfly Groin Stretch"],
                    recovery="Consume a balanced mix of vegetables, healthy fats (olive oil/nuts), and lean protein."
                ),
                DayPlanSchema(
                    day=5,
                    day_name="Day 5 - Upper Body & Core Alignment",
                    focus="Shoulder, Back & Core Wellness",
                    warmup=["Arm circles", "Doorway chest stretch"],
                    exercises=[
                        ExerciseSchema(name="Dumbbell Overhead Press (Light/Moderate)", sets=3, reps="10-12 reps", rest_seconds=60, notes="Maintain upright spine, no arching in lower back"),
                        ExerciseSchema(name="Resistance Band / DB Lat Pulls", sets=3, reps="12 reps", rest_seconds=60, notes="Strengthen postural muscles"),
                        ExerciseSchema(name="Deadbugs", sets=3, reps="10 reps/side", rest_seconds=45, notes="Press lower back flat into the ground"),
                    ],
                    cooldown=["Upper Trapezius Neck Stretch", "Cross-body shoulder stretch"],
                    recovery="Spend 10 minutes unplugged from screens before bedtime."
                ),
                DayPlanSchema(
                    day=6,
                    day_name="Day 6 - Active Leisure / Recreational Movement",
                    focus="Mindful Movement & Outdoor Activity",
                    warmup=["Gentle whole body stretch"],
                    exercises=[
                        ExerciseSchema(name="Nature Hike / Swimming / Cycling", sets=1, reps="30-45 mins", rest_seconds=0, notes="Enjoyable physical recreation at a relaxed pace"),
                    ],
                    cooldown=["Full body relaxation stretches"],
                    recovery="Stay well-hydrated throughout the day."
                ),
                DayPlanSchema(
                    day=7,
                    day_name="Day 7 - Rest, Meditation & Reset",
                    focus="Complete Body & Mind Rejuvenation",
                    warmup=[],
                    exercises=[
                        ExerciseSchema(name="Gentle 10-min Morning Mobility", sets=1, reps="10 mins", rest_seconds=0, notes="Gentle neck rolls, side bends, and deep breathing"),
                    ],
                    cooldown=["Full body relaxation"],
                    recovery="Reflect on weekly achievements and prepare for next week with enthusiasm."
                )
            ]

        return WorkoutPlanContentSchema(
            title=f"7-Day Personalized {goal} Plan for {name}",
            goal=goal_enum,
            intensity=intensity_enum,
            experience_level=exp_enum,
            summary=f"A targeted 7-day program specifically calibrated for {goal.lower()} with {intensity.lower()} intensity for {name}.",
            safety_disclaimer="Always consult a certified healthcare professional before beginning any exercise routine. Listen to your body and stop immediately if you experience sharp or unusual pain.",
            days=days
        )

    def _refine_deterministic_plan(
        self,
        current_plan_dict: Dict[str, Any],
        feedback_text: str,
        goal: str,
        intensity: str
    ) -> WorkoutPlanContentSchema:
        """Modifies existing plan structure deterministically based on feedback cues."""
        fb_lower = feedback_text.lower()
        plan_copy = json.loads(json.dumps(current_plan_dict))

        # Adjust based on feedback keyword cues
        if "cardio" in fb_lower:
            for day in plan_copy.get("days", []):
                if day.get("day") in [2, 4, 6]:
                    day["exercises"].append({
                        "name": "Brisk Cardio Interval (HIIT / Steady State)",
                        "sets": 3,
                        "reps": "5 mins",
                        "rest_seconds": 60,
                        "notes": "Added per user feedback for cardiovascular focus"
                    })
        elif "rest" in fb_lower:
            # Convert day 4 or 6 into active recovery
            for day in plan_copy.get("days", []):
                if day.get("day") == 4:
                    day["focus"] = "Active Recovery & Gentle Mobility (Feedback Updated)"
                    day["exercises"] = [
                        {
                            "name": "Full Body Foam Rolling & Gentle Stretch",
                            "sets": 1,
                            "reps": "20 mins",
                            "rest_seconds": 0,
                            "notes": "Added rest day per user feedback"
                        }
                    ]
        elif "easier" in fb_lower or "reduce" in fb_lower:
            for day in plan_copy.get("days", []):
                for ex in day.get("exercises", []):
                    if isinstance(ex.get("sets"), int) and ex["sets"] > 2:
                        ex["sets"] -= 1
                    if isinstance(ex.get("rest_seconds"), int):
                        ex["rest_seconds"] += 15
        elif "upper" in fb_lower:
            for day in plan_copy.get("days", []):
                if day.get("day") in [1, 3]:
                    day["exercises"].append({
                        "name": "Upper Body Push-Ups / Dumbbell Overhead Press",
                        "sets": 3,
                        "reps": "10-12 reps",
                        "rest_seconds": 60,
                        "notes": "Enhanced upper body emphasis"
                    })

        plan_copy["title"] = f"{plan_copy.get('title', '7-Day Workout Plan')} (Refined)"
        plan_copy["summary"] = f"Updated based on your feedback: '{feedback_text}'."

        return WorkoutPlanContentSchema.model_validate(plan_copy)

    def _get_fallback_nutrition_tip(self, goal: str) -> str:
        """Returns standard expert nutrition tips for each fitness goal."""
        tips = {
            "Weight Loss": "Prioritize nutrient-dense whole foods and lean proteins (aim for 1.6-2.0g per kg of body weight) while maintaining a moderate 300-500 calorie deficit. Ensure you drink at least 2.5-3 liters of water daily to support metabolism and suppress false hunger cues.",
            "Muscle Gain": "Consume adequate dietary protein distributed across 4-5 meals daily (aim for 1.8-2.2g per kg of body weight) and maintain a modest 250-400 calorie surplus. Prioritize 8 hours of deep sleep to maximize muscle protein synthesis and growth hormone release.",
            "General Wellness": "Prioritize balanced meals rich in colorful vegetables, healthy unsaturated fats, fiber, and quality protein. Maintain daily hydration, limit ultra-processed sugars, and take a 10-minute post-dinner walk to promote steady blood glucose regulation."
        }
        return tips.get(goal, tips["General Wellness"])


gemini_service = GeminiService()
