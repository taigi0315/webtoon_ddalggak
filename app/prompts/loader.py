from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

_PROMPTS_PATH = Path(__file__).resolve().parent / "prompts.yaml"


@lru_cache(maxsize=1)
def _load_prompts() -> dict[str, Any]:
    with _PROMPTS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("prompts.yaml must be a mapping at top level")
    return data


def get_prompt(name: str) -> str:
    value = _load_prompts().get(name)
    if not isinstance(value, str):
        raise KeyError(f"Prompt '{name}' not found or not a string")
    return value


def get_prompt_data(name: str) -> Any:
    if name not in _load_prompts():
        raise KeyError(f"Prompt data '{name}' not found")
    return _load_prompts()[name]


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(name: str, **context: Any) -> str:
    template = get_prompt(name)
    return _jinja_env().from_string(template).render(**context).strip()
