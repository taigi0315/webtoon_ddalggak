import json
import logging
import re

from app.core.metrics import increment_json_parse_failure
from app.graphs.nodes.constants import SYSTEM_PROMPT_JSON
from app.prompts.loader import render_prompt
from app.services.vertex_gemini import GeminiClient

logger = logging.getLogger(__name__)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    patterns = [
        r"```json\s*\n?(.*?)\n?```",
        r"```\s*\n?(.*?)\n?```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return text


def _clean_json_text(text: str) -> str:
    """Clean common LLM JSON output issues."""
    cleaned = text.strip()
    cleaned = _strip_markdown_fences(cleaned)

    lines = cleaned.split("\n")

    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            start_idx = i
            break

    end_idx = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.endswith("}") or stripped.endswith("]"):
            end_idx = i
            break

    cleaned = "\n".join(lines[start_idx : end_idx + 1])

    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    return cleaned.strip()


def _extract_json_object(text: str) -> str | None:
    """Extract the outermost JSON object using bracket matching."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _extract_json_array(text: str) -> str | None:
    """Extract the outermost JSON array using bracket matching."""
    start = text.find("[")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _repair_json_with_llm(
    gemini: GeminiClient,
    malformed_text: str,
    expected_schema: str | None = None,
    max_repair_attempts: int = 2,
) -> dict | list | None:
    """Attempt to repair malformed JSON using LLM with retries."""
    schema_hint = ""
    if expected_schema:
        schema_hint = f"\n\nExpected schema:\n{expected_schema}"

    for attempt in range(max_repair_attempts):
        repair_prompt = render_prompt(
            "prompt_repair_json",
            system_prompt_json=SYSTEM_PROMPT_JSON,
            schema_hint=schema_hint,
            malformed_text=malformed_text[:2000],
        )

        try:
            repaired = gemini.generate_text(prompt=repair_prompt)

            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                increment_json_parse_failure("repair_raw")
                pass

            cleaned = _clean_json_text(repaired)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                increment_json_parse_failure("repair_cleaned")
                pass

            obj_text = _extract_json_object(repaired)
            if obj_text:
                try:
                    return json.loads(obj_text)
                except json.JSONDecodeError:
                    increment_json_parse_failure("repair_object")
                    pass

            arr_text = _extract_json_array(repaired)
            if arr_text:
                try:
                    return json.loads(arr_text)
                except json.JSONDecodeError:
                    increment_json_parse_failure("repair_array")
                    pass

            logger.warning(
                "JSON repair attempt %d/%d failed to produce valid JSON",
                attempt + 1,
                max_repair_attempts,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "JSON repair attempt %d/%d raised exception: %s",
                attempt + 1,
                max_repair_attempts,
                exc,
            )

    return None


def _maybe_json_from_gemini(
    gemini: GeminiClient,
    prompt: str,
    expected_schema: str | None = None,
) -> dict | list | None:
    """
    Multi-tier JSON extraction with self-repair.
    """
    full_prompt = f"{SYSTEM_PROMPT_JSON}\n\n{prompt}"

    try:
        text = gemini.generate_text(prompt=full_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("gemini prompt failed: %s", exc)
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        increment_json_parse_failure("direct")
        pass

    cleaned_text = _clean_json_text(text)
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        increment_json_parse_failure("cleaned")
        pass

    obj_text = _extract_json_object(text)
    if obj_text:
        try:
            return json.loads(obj_text)
        except json.JSONDecodeError:
            increment_json_parse_failure("object")
            pass

    arr_text = _extract_json_array(text)
    if arr_text:
        try:
            return json.loads(arr_text)
        except json.JSONDecodeError:
            increment_json_parse_failure("array")
            pass

    logger.info(
        "All direct JSON parsing failed, attempting LLM repair. Preview: %s",
        text[:200] if text else "empty",
    )

    result = _repair_json_with_llm(gemini, text, expected_schema)
    if result is not None:
        logger.info("JSON parsed successfully via LLM repair")
        return result

    logger.warning(
        "All JSON parsing methods failed. Text preview: %s",
        text[:300] if text else "empty",
    )
    return None
