import math

from app.graphs.nodes.constants import VALID_GRAMMAR_IDS
from app.graphs.nodes.helpers.scene import _choose_mid_grammar


def _heuristic_panel_plan(scene_text: str, panel_count: int) -> dict:
    panels: list[dict] = []
    for idx in range(panel_count):
        if idx == 0:
            grammar_id = "establishing"
        elif idx == panel_count - 1:
            grammar_id = "reaction"
        else:
            grammar_id = _choose_mid_grammar(scene_text)
        panels.append(
            {
                "panel_index": idx + 1,
                "grammar_id": grammar_id,
                "story_function": _grammar_story_function(grammar_id),
            }
        )
    return {"panels": panels}


def _grammar_story_function(grammar_id: str) -> str:
    mapping = {
        "establishing": "setup",
        "dialogue_medium": "dialogue",
        "emotion_closeup": "emotion",
        "action": "action",
        "reaction": "reaction",
        "object_focus": "focus",
        "reveal": "climax",
        "impact_silence": "climax",
    }
    return mapping.get(grammar_id, "beat")


def _normalize_panel_plan(panel_plan: dict) -> dict:
    panels = list(panel_plan.get("panels") or [])
    if not panels:
        return {"panels": []}

    # Validate grammar_ids and replace invalid ones
    for panel in panels:
        grammar_id = panel.get("grammar_id")
        if grammar_id not in VALID_GRAMMAR_IDS:
            panel["grammar_id"] = "dialogue_medium"
            if not panel.get("story_function"):
                panel["story_function"] = _grammar_story_function("dialogue_medium")
        
        # Ensure story_function is populated
        if not panel.get("story_function"):
            panel["story_function"] = _grammar_story_function(panel.get("grammar_id", "dialogue_medium"))

    # We removed strict constraints (establishing start, max closeups, repeated framing)
    # to allow the LLM's visual intent to drive the plan.

    return {"panels": panels}


def _panel_purpose_from(panel: dict) -> str:
    grammar_id = panel.get("grammar_id")
    story_function = panel.get("story_function")
    if story_function:
        return str(story_function)
    mapping = {
        "dialogue_medium": "dialogue",
        "emotion_closeup": "reaction",
        "reaction": "reaction",
        "action": "action",
        "object_focus": "reveal",
        "reveal": "reveal",
        "impact_silence": "silent_beat",
        "establishing": "establishing",
    }
    return mapping.get(grammar_id, "dialogue")


def _annotate_panel_utility(panel: dict) -> dict:
    panel_role = panel.get("panel_role")
    if panel_role not in {"main", "inset"}:
        panel_role = "main"
    panel["panel_role"] = panel_role

    panel_purpose = panel.get("panel_purpose")
    if panel_purpose not in {
        "dialogue",
        "reaction",
        "reveal",
        "action",
        "establishing",
        "silent_beat",
    }:
        panel_purpose = _panel_purpose_from(panel)
    panel["panel_purpose"] = panel_purpose

    has_dialogue = panel.get("has_dialogue")
    if not isinstance(has_dialogue, bool):
        has_dialogue = panel.get("grammar_id") == "dialogue_medium" or panel_purpose == "dialogue"
    panel["has_dialogue"] = has_dialogue

    if has_dialogue:
        utility = 1.0
    elif panel_purpose in {"reveal", "reaction", "action"}:
        utility = 0.7
    elif panel_purpose == "silent_beat":
        utility = 0.4
    elif panel_purpose == "establishing":
        utility = 0.5
    else:
        utility = 0.3
    panel["utility_score"] = float(panel.get("utility_score", utility))
    return panel


def _evaluate_and_prune_panel_plan(panel_plan: dict) -> dict:
    panels = list(panel_plan.get("panels") or [])
    if not panels:
        return {"panels": []}

    annotated = [_annotate_panel_utility(dict(panel)) for panel in panels]

    meaningful = {"reveal", "reaction", "action", "silent_beat"}
    pruned = []
    inset_panels = []
    for panel in annotated:
        is_inset = panel.get("panel_role") == "inset"
        if is_inset and not panel.get("has_dialogue") and panel.get("panel_purpose") not in meaningful:
            continue
        if is_inset:
            inset_panels.append(panel)
        pruned.append(panel)

    if len(inset_panels) > 2:
        inset_panels_sorted = sorted(inset_panels, key=lambda p: p.get("utility_score", 0))
        to_drop = {p.get("panel_index") for p in inset_panels_sorted[:-2]}
        pruned = [p for p in pruned if p.get("panel_index") not in to_drop]

    for idx, panel in enumerate(pruned, start=1):
        panel["panel_index"] = idx

    return {"panels": pruned}


def _assign_panel_weights(panel_plan: dict, scene_importance: str | None = None) -> dict:
    """Add `weight` (0.1-1.0) and `must_be_large` to each panel based on importance or utility."""
    panels = list(panel_plan.get("panels") or [])
    if not panels:
        return panel_plan

    # Check for explicit importance_weight from LLM
    has_explicit = any(p.get("importance_weight") is not None for p in panels)

    if has_explicit:
        for p in panels:
            w = p.get("importance_weight")
            try:
                weight = float(w) if w is not None else 0.5
            except (ValueError, TypeError):
                weight = 0.5
            
            p["weight"] = round(min(max(weight, 0.1), 1.0), 3)
            
            # Simple heuristic for dominant panels if scene is critical
            must = bool(p.get("must_be_large", False))
            if not must and scene_importance in {"climax", "cliffhanger"} and weight > 0.75:
                must = True
            p["must_be_large"] = must
        return {"panels": panels}

    # Fallback: Utility-based weight assignment
    utilities = [p.get("utility_score", 0.3) for p in panels]
    min_u = min(utilities)
    max_u = max(utilities)
    range_u = max(max_u - min_u, 1e-6)

    for p in panels:
        u = float(p.get("utility_score", 0.3))
        norm = (u - min_u) / range_u if range_u > 0 else 0.0
        weight = 0.12 + norm * (1.0 - 0.12)
        explicit = p.get("weight")
        if isinstance(explicit, (int, float)):
            try:
                ew = float(explicit)
                weight = min(max(ew, 0.1), 1.0)
            except Exception:
                pass
        p["weight"] = round(float(weight), 3)

        must = bool(p.get("must_be_large", False))
        purpose = p.get("panel_purpose")
        if not must and purpose in {"reveal", "reaction"} and scene_importance in {"climax", "cliffhanger"}:
            must = True
        p["must_be_large"] = must

    return {"panels": panels}
