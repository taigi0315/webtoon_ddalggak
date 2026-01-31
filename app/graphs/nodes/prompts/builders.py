import json
import uuid

from app.db.models import Character
from app.graphs.nodes.constants import GLOBAL_CONSTRAINTS, SYSTEM_PROMPT_JSON
from app.graphs.nodes.helpers.character import get_character_style_prompt
from app.graphs.nodes.helpers.dialogue import _dialogue_panel_ids
from app.prompts.loader import render_prompt


def _prompt_dialogue_script(
    scene_id: uuid.UUID,
    scene_text: str,
    panel_semantics: dict,
    character_names: list[str],
) -> str:
    panel_ids = _dialogue_panel_ids(panel_semantics)
    panels = panel_semantics.get("panels") if isinstance(panel_semantics, dict) else []
    panel_lines = []
    for panel in panels or []:
        if not isinstance(panel, dict):
            continue
        pid = panel.get("panel_index") or panel.get("panel_id")
        desc = panel.get("description") or ""
        panel_lines.append(f"- Panel {pid}: {desc}")
    panel_lines_text = "\n".join(panel_lines) if panel_lines else "No panel descriptions available."
    char_list = ", ".join(character_names) if character_names else "Unknown"

    return render_prompt(
        "prompt_dialogue_script",
        scene_id=scene_id,
        scene_text=scene_text,
        panel_lines_text=panel_lines_text,
        char_list=char_list,
    )


def _prompt_variant_suggestions(
    story_id: uuid.UUID,
    story_title: str,
    scene_text: str,
    character_names: list[str],
) -> str:
    char_list = ", ".join(character_names) if character_names else "Unknown"
    return render_prompt(
        "prompt_variant_suggestions",
        story_id=story_id,
        story_title=story_title,
        scene_text=scene_text,
        char_list=char_list,
    )


def _prompt_scene_intent(scene_text: str, character_names: list[str] | None = None) -> str:
    """Production-grade scene intent extraction prompt."""
    char_list = ", ".join(character_names) if character_names else "unknown"

    return render_prompt(
        "prompt_scene_intent",
        global_constraints=GLOBAL_CONSTRAINTS,
        char_list=char_list,
        scene_text=scene_text,
    )


def _prompt_panel_plan(
    scene_text: str,
    panel_count: int,
    scene_intent: dict | None = None,
    scene_importance: str | None = None,
    character_names: list[str] | None = None,
    qc_rules: dict | None = None,
) -> str:
    """Production-grade panel plan generation prompt."""
    intent_block = ""
    if scene_intent:
        intent_block = f"""
Scene Intent:
- Logline: {scene_intent.get('logline', 'N/A')}
- Pacing: {scene_intent.get('pacing', 'normal')}
- Emotional arc: {scene_intent.get('emotional_arc', {})}
"""
    importance_block = ""
    if scene_importance:
        importance_block = f"\nScene importance: {scene_importance}\n"

    char_list = ", ".join(character_names) if character_names else "unknown characters"

    qc_block = ""
    if qc_rules:
        qc_block = f"""
QC HARD CONSTRAINTS (you MUST follow these):
- Max closeup ratio: {qc_rules.get('closeup_ratio_max', 0.5)} (no more than {int(panel_count * qc_rules.get('closeup_ratio_max', 0.5))} emotion_closeup panels)
- No more than 2 consecutive panels with the same grammar_id
- First panel MUST be 'establishing'
- Last panel SHOULD be 'reaction' or 'reveal' for closure
- Inset panels must be meaningful (dialogue, reveal, reaction, action, or intentional silent beat)
- Max inset panels: 2
"""

    return render_prompt(
        "prompt_panel_plan",
        global_constraints=GLOBAL_CONSTRAINTS,
        panel_count=panel_count,
        intent_block=intent_block.strip(),
        importance_block=importance_block.strip(),
        char_list=char_list,
        qc_block=qc_block.strip(),
        scene_text=scene_text,
    )


def _prompt_panel_semantics(
    scene_text: str,
    panel_plan: dict,
    layout_template: dict,
    characters: list[Character],
    scene_intent: dict | None = None,
) -> str:
    """Production-grade panel semantics prompt with grammar constraints."""
    char_blocks = []
    for c in characters:
        identity = c.identity_line or f"{c.name}: {c.role or 'character'}"
        char_block = f"  - {identity}"

        gender = getattr(c, "gender", None)
        age_range = getattr(c, "age_range", None)
        if gender and age_range:
            char_style = get_character_style_prompt(gender, age_range)
            if char_style:
                char_block += f"\n    [Age/Style reference: {char_style[:300]}]"

        appearance = getattr(c, "appearance", None)
        if isinstance(appearance, dict):
            appearance_parts = []
            if appearance.get("hair"):
                appearance_parts.append(f"hair: {appearance['hair']}")
            if appearance.get("build"):
                appearance_parts.append(f"build: {appearance['build']}")
            if appearance_parts:
                char_block += f"\n    [Visual: {', '.join(appearance_parts)}]"

        char_blocks.append(char_block)
    char_section = "\n".join(char_blocks) if char_blocks else "  - No specific characters"

    panels_summary = []
    for p in panel_plan.get("panels", []):
        panels_summary.append(f"  Panel {p.get('panel_index')}: {p.get('grammar_id')} - {p.get('beat_summary', p.get('story_function', ''))}")
    plan_section = "\n".join(panels_summary)

    intent_block = ""
    if scene_intent:
        intent_block = f"""
Scene Context:
- Logline: {scene_intent.get('logline', 'N/A')}
- Pacing: {scene_intent.get('pacing', 'normal')}
- Visual motifs to include: {scene_intent.get('visual_motifs', [])}
"""

    return render_prompt(
        "prompt_panel_semantics",
        global_constraints=GLOBAL_CONSTRAINTS,
        intent_block=intent_block.strip(),
        char_section=char_section,
        plan_section=plan_section,
        layout_text=layout_template.get("layout_text", "vertical scroll"),
        scene_text=scene_text,
    )


def _prompt_blind_reader(panel_semantics: dict) -> str:
    """Stage 1: Blind reader reconstructs story from panel semantics only."""
    panels_desc = []
    for p in panel_semantics.get("panels", []):
        desc = f"Panel {p.get('panel_index')}: {p.get('description', '')}"
        dialogue = p.get("dialogue", [])
        if dialogue:
            dialogue_texts: list[str] = []
            if isinstance(dialogue, list):
                for item in dialogue:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            dialogue_texts.append(str(text))
                    else:
                        dialogue_texts.append(str(item))
            else:
                dialogue_texts.append(str(dialogue))
            if dialogue_texts:
                desc += f" Dialogue: {' '.join(dialogue_texts)}"
        chars = p.get("characters", [])
        if isinstance(chars, list) and chars:
            if isinstance(chars[0], dict):
                char_names = [c.get("name", "someone") for c in chars]
            else:
                char_names = chars
            desc += f" Characters: {', '.join(char_names)}"
        panels_desc.append(desc)

    return render_prompt(
        "prompt_blind_reader",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        panel_descriptions="\n".join(panels_desc),
    )


def _prompt_comparator(original_text: str, blind_reading: dict) -> str:
    """Stage 2: Compare blind reading to original for scoring."""
    return render_prompt(
        "prompt_comparator",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        original_text=original_text,
        reconstructed_story=blind_reading.get("reconstructed_story", "N/A"),
        identified_characters=blind_reading.get("identified_characters", []),
        plot_points=blind_reading.get("plot_points", []),
        unclear_elements=blind_reading.get("unclear_elements", []),
    )


def _prompt_blind_test(scene_text: str, panel_semantics: dict) -> str:
    """Fallback single-prompt blind test (used if two-stage fails)."""
    panels_desc = []
    for p in panel_semantics.get("panels", []):
        desc = f"Panel {p.get('panel_index')}: {p.get('description', '')}"
        dialogue = p.get("dialogue", [])
        if dialogue:
            desc += f" Dialogue: {' '.join(dialogue)}"
        panels_desc.append(desc)

    return render_prompt(
        "prompt_blind_test",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        scene_text=scene_text,
        panel_descriptions="\n".join(panels_desc),
    )


def _prompt_character_extraction(source_text: str, max_characters: int) -> str:
    """Prompt for LLM-based character extraction."""
    return render_prompt(
        "prompt_character_extraction",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        max_characters=max_characters,
        source_text=source_text,
    )


def _prompt_character_normalization(characters: list[dict], source_text: str) -> str:
    """Prompt for LLM-based character enrichment with Korean manhwa aesthetics."""
    char_list = json.dumps(characters, indent=2)

    return render_prompt(
        "prompt_character_normalization",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        characters_json=char_list,
        story_context=source_text[:1500],
    )


def _prompt_visual_plan(
    scenes: list[dict],
    characters: list[dict],
) -> str:
    """Prompt for LLM-based visual plan compilation."""
    char_identities = []
    for c in characters:
        identity = c.get("identity_line") or f"{c.get('name', 'Unknown')}: {c.get('role', 'character')}"
        char_identities.append(f"  - {identity}")

    scenes_block = []
    for s in scenes:
        scenes_block.append(f"Scene {s.get('scene_index', '?')}:\n{s.get('source_text', s.get('summary', ''))[:500]}")

    return render_prompt(
        "prompt_visual_plan",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        character_identities="\n".join(char_identities),
        scenes_block="\n".join(scenes_block),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
