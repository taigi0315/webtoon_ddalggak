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
