from app.prompts.loader import get_prompt

ARTIFACT_SCENE_INTENT = "scene_intent"
ARTIFACT_PANEL_PLAN = "panel_plan"
ARTIFACT_PANEL_PLAN_NORMALIZED = "panel_plan_normalized"
ARTIFACT_LAYOUT_TEMPLATE = "layout_template"
ARTIFACT_PANEL_SEMANTICS = "panel_semantics"
ARTIFACT_RENDER_SPEC = "render_spec"
ARTIFACT_RENDER_RESULT = "render_result"
ARTIFACT_QC_REPORT = "qc_report"
ARTIFACT_BLIND_TEST_REPORT = "blind_test_report"
ARTIFACT_DIALOGUE_SUGGESTIONS = "dialogue_suggestions"
ARTIFACT_VISUAL_PLAN = "visual_plan"
ARTIFACT_ART_DIRECTION = "art_direction"
ARTIFACT_TRANSITION_MAP = "transition_map"
ARTIFACT_CLOSURE_PLAN = "closure_plan"
ARTIFACT_VERTICAL_RHYTHM = "vertical_rhythm_map"
ARTIFACT_METAPHOR_DIRECTIONS = "metaphor_directions"
ARTIFACT_PRESENCE_MAP = "presence_map"

SYSTEM_PROMPT_JSON = get_prompt("system_prompt_json")
GLOBAL_CONSTRAINTS = get_prompt("global_constraints")
VISUAL_PROMPT_FORMULA = get_prompt("visual_prompt_formula")

VALID_GRAMMAR_IDS = frozenset([
    "establishing",
    "dialogue_medium",
    "emotion_closeup",
    "action",
    "reaction",
    "object_focus",
    "reveal",
    "impact_silence",
])

VALID_GAZE_VALUES = frozenset([
    "at_other",
    "at_object",
    "down",
    "away",
    "toward_path",
    "camera",
])

PACING_OPTIONS = frozenset([
    "slow_burn",
    "normal",
    "fast",
    "impact",
])

GENRE_PROFILES = {
    "action": {
        "panel_count_range": (60, 70),
        "required_shot_types": ["action", "reaction"],
        "forbidden_transitions": []
    },
    "fantasy": {
        "panel_count_range": (50, 60),
        "required_shot_types": ["establishing"],
        "forbidden_transitions": []
    },
    "romance": {
        "panel_count_range": (40, 50),
        "required_shot_types": ["emotion_closeup", "reaction"],
        "forbidden_transitions": []
    },
    "drama": {
        "panel_count_range": (40, 50),
        "required_shot_types": ["emotion_closeup", "reaction"],
        "forbidden_transitions": []
    },
    "comedy": {
        "panel_count_range": (30, 40),
        "required_shot_types": ["reaction"],
        "forbidden_transitions": ["aspect_to_aspect"]
    }
}
