import re

_NARRATION_LIKE_PHRASES = (
    " he says",
    " she says",
    " he whispers",
    " she whispers",
    " he thinks",
    " she thinks",
    " he stares",
    " she stares",
    " he looks",
    " she looks",
    " he walks",
    " she walks",
    " he steps",
    " she steps",
    "as if",
    "suddenly",
    "meanwhile",
)

_GENERIC_DIALOGUE_PATTERNS = (
    "as you know",
    "let me explain",
    "in other words",
    "we need to",
    "i cannot believe this is happening",
    "this changes everything",
    "i have a bad feeling about this",
)


def _extract_dialogue_lines(text: str) -> list[str]:
    lines = []
    for match in re.findall(r"“([^”]+)”", text):
        lines.append(match.strip())
    for match in re.findall(r"\"([^\"]+)\"", text):
        line = match.strip()
        if line and line not in lines:
            lines.append(line)
    return lines


def _dialogue_panel_ids(panel_semantics: dict) -> list[int]:
    panels = panel_semantics.get("panels") if isinstance(panel_semantics, dict) else None
    if not isinstance(panels, list) or not panels:
        return []
    panel_ids: list[int] = []
    for idx, panel in enumerate(panels):
        if isinstance(panel, dict):
            panel_id = panel.get("panel_index") or panel.get("panel_id")
            if isinstance(panel_id, int):
                panel_ids.append(panel_id)
                continue
        panel_ids.append(idx + 1)
    return panel_ids


def _normalize_dialogue_script(raw: dict | None, panel_ids: list[int]) -> dict:
    normalized = {"scene_id": None, "dialogue_by_panel": []}
    if isinstance(raw, dict):
        normalized["scene_id"] = raw.get("scene_id")
        raw_panels = raw.get("dialogue_by_panel")
        if isinstance(raw_panels, list):
            normalized["dialogue_by_panel"] = raw_panels

    panel_map = {p.get("panel_id"): p for p in normalized.get("dialogue_by_panel", []) if isinstance(p, dict)}
    result_panels = []

    def _is_narration_like(text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in _NARRATION_LIKE_PHRASES)

    def _is_generic_dialogue(text: str) -> bool:
        lowered = text.lower()
        return any(p in lowered for p in _GENERIC_DIALOGUE_PATTERNS)

    def _trim_words(text: str, limit: int = 15) -> str:
        words = text.split()
        if len(words) <= limit:
            return text
        return " ".join(words[:limit]).rstrip(" ,.;:") + "..."

    for panel_id in panel_ids:
        panel = panel_map.get(panel_id, {"panel_id": panel_id, "lines": [], "notes": None})
        lines = panel.get("lines")
        cleaned_lines = []
        caption_used = False
        seen_texts: set[str] = set()
        if isinstance(lines, list):
            for line in lines:
                if not isinstance(line, dict):
                    continue
                text = str(line.get("text") or "").strip()
                if not text:
                    continue
                speaker = str(line.get("speaker") or "unknown").strip() or "unknown"
                line_type = str(line.get("type") or "speech").strip().lower()
                if line_type not in {"speech", "thought", "caption", "sfx"}:
                    line_type = "speech"
                if _is_narration_like(text) and line_type in {"speech", "thought"}:
                    continue
                if _is_generic_dialogue(text) and line_type in {"speech", "thought"}:
                    continue
                if line_type == "caption":
                    if caption_used:
                        continue
                    caption_used = True
                normalized_text = _trim_words(text, 15 if line_type in {"speech", "thought"} else 18)
                dedupe_key = f"{line_type}:{normalized_text.lower()}"
                if dedupe_key in seen_texts:
                    continue
                seen_texts.add(dedupe_key)
                cleaned_lines.append({"speaker": speaker, "type": line_type, "text": normalized_text})
                if len(cleaned_lines) >= 3:
                    break
        result_panels.append(
            {
                "panel_id": panel_id,
                "lines": cleaned_lines,
                "notes": panel.get("notes"),
            }
        )
    normalized["dialogue_by_panel"] = result_panels
    return normalized


def _fallback_dialogue_script(scene_text: str, panel_ids: list[int]) -> dict:
    dialogue_lines = _extract_dialogue_lines(scene_text)
    lines_iter = iter(dialogue_lines)
    panels = []
    for panel_id in panel_ids:
        panel_lines = []
        for _ in range(3):
            line = next(lines_iter, None)
            if not line:
                break
            panel_lines.append({"speaker": "unknown", "type": "speech", "text": line})
        panels.append({"panel_id": panel_id, "lines": panel_lines, "notes": None})
    return {"scene_id": None, "dialogue_by_panel": panels}
