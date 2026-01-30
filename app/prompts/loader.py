"""
Prompt loader with versioning and domain organization support.

This loader supports both the legacy single-file prompts.yaml and the new
# Updated for prompt optimization
versioned directory structure:

    v1/
    ├── shared/           # System prompts, constraints, style maps
    ├── story_build/      # Character extraction, normalization, visual plan
    ├── scene_planning/   # Scene intent, panel plan, panel semantics
    ├── evaluation/       # Blind test prompts
    ├── dialogue/         # Dialogue script, variant suggestions
    └── utility/          # JSON repair

Usage:
    from app.prompts.loader import get_prompt, render_prompt, get_prompt_data

    # Get raw prompt template
    template = get_prompt("prompt_scene_intent")

    # Render with variables
    rendered = render_prompt("prompt_scene_intent", scene_text="...", genre_text="...")

    # Get non-string data (e.g., character_style_map)
    style_map = get_prompt_data("character_style_map")
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent
_LEGACY_PROMPTS_PATH = _PROMPTS_DIR / "prompts.yaml"
_VERSION = "v1"

# Domain to subdirectory mapping for organized prompts
_DOMAIN_DIRS = [
    "shared",
    "story_build",
    "scene_planning",
    "evaluation",
    "dialogue",
    "utility",
]


@lru_cache(maxsize=1)
def _load_legacy_prompts() -> dict[str, Any]:
    """Load prompts from legacy single-file prompts.yaml."""
    if not _LEGACY_PROMPTS_PATH.exists():
        return {}
    with _LEGACY_PROMPTS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("prompts.yaml must be a mapping at top level")
    return data


@lru_cache(maxsize=1)
def _load_versioned_prompts() -> dict[str, Any]:
    """Load prompts from versioned directory structure."""
    prompts: dict[str, Any] = {}
    version_dir = _PROMPTS_DIR / _VERSION

    if not version_dir.exists():
        return prompts

    for domain in _DOMAIN_DIRS:
        domain_dir = version_dir / domain
        if not domain_dir.exists():
            continue

        for yaml_file in domain_dir.glob("*.yaml"):
            # Read YAML file but don't swallow template syntax errors (we want CI to fail fast)
            try:
                with yaml_file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read {yaml_file}: {e}")
                continue

            if not isinstance(data, dict):
                continue

            # Validate Jinja2 templates in string values to fail fast during CI
            for key, value in list(data.items()):
                if isinstance(value, str):
                    try:
                        # parse will raise TemplateSyntaxError for invalid templates
                        _jinja_env().parse(value)
                    except Exception as e:  # TemplateSyntaxError or others
                        raise ValueError(f"Invalid Jinja2 template in {yaml_file}:{key}: {e}") from e

            prompts.update(data)

    return prompts


@lru_cache(maxsize=1)
def _load_prompts() -> dict[str, Any]:
    """
    Load all prompts with versioned prompts taking precedence over legacy.

    Returns a merged dict where versioned prompts override legacy prompts
    with the same key.
    """
    legacy = _load_legacy_prompts()
    versioned = _load_versioned_prompts()

    # Merge with versioned taking precedence
    merged = {**legacy, **versioned}
    return merged


def get_prompt(name: str, version: str | None = None) -> str:
    """
    Get a prompt template by name.

    Supports two prompt shapes in versioned YAML files:
    - String value: { name: "template string" }
    - Mapping value: { name: { template: "...", required_variables: [...], output_schema: {...} } }

    Args:
        name: The prompt key (e.g., "prompt_scene_intent")
        version: Optional version override (default: use current version)

    Returns:
        The prompt template string

    Raises:
        KeyError: If prompt not found or not a string
    """
    prompts = _load_prompts()
    value = prompts.get(name)
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "template" in value:
        return value["template"]
    raise KeyError(f"Prompt '{name}' not found or not a string")


def get_prompt_data(name: str) -> Any:
    """
    Get prompt data that may not be a string (e.g., character_style_map) or
    a prompt mapping with metadata.

    Args:
        name: The data key

    Returns:
        The data value (dict, list, or string)

    Raises:
        KeyError: If key not found
    """
    prompts = _load_prompts()
    if name not in prompts:
        raise KeyError(f"Prompt data '{name}' not found")
    return prompts[name]


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    """Create Jinja2 environment for prompt rendering."""
    return Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(name: str, validate: bool = False, **context: Any) -> str:
    """
    Render a prompt template with the given context.

    Shared prompts (system_prompt_json, global_constraints) are automatically
    included in the context if not explicitly provided.

    Args:
        name: The prompt key
        validate: If True, validate that all required variables are provided
        **context: Variables to render into the template

    Returns:
        The rendered prompt string

    Raises:
        ValueError: If validate=True and required variables are missing
    """
    # Auto-include shared prompts if not in context
    prompts = _load_prompts()
    for shared_key in ["system_prompt_json", "global_constraints"]:
        if shared_key not in context and shared_key in prompts:
            context[shared_key] = prompts[shared_key]

    # Validate required variables if requested
    if validate:
        missing = check_required_variables(name, context)
        if missing:
            raise ValueError(f"Missing required variables for '{name}': {missing}")

    template = get_prompt(name)
    return _jinja_env().from_string(template).render(**context).strip()


def list_prompts(domain: str | None = None) -> list[str]:
    """
    List available prompt names.

    Args:
        domain: Optional domain filter (e.g., "scene_planning")

    Returns:
        List of prompt names
    """
    if domain is None:
        return list(_load_prompts().keys())

    # Load only from specific domain
    domain_dir = _PROMPTS_DIR / _VERSION / domain
    if not domain_dir.exists():
        return []

    prompts = []
    for yaml_file in domain_dir.glob("*.yaml"):
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                prompts.extend(data.keys())
        except Exception:
            pass
    return prompts


def get_prompt_metadata(name: str) -> dict[str, Any]:
    """
    Get metadata about a prompt (domain, version, file path, variables,
    required_variables, output_schema).

    Args:
        name: The prompt name

    Returns:
        Dict with domain, version, file_path, variables, required_variables,
        and output_schema (if present)
    """
    version_dir = _PROMPTS_DIR / _VERSION

    for domain in _DOMAIN_DIRS:
        domain_dir = version_dir / domain
        if not domain_dir.exists():
            continue

        for yaml_file in domain_dir.glob("*.yaml"):
            try:
                with yaml_file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict) and name in data:
                    entry = data[name]
                    template = entry if isinstance(entry, str) else entry.get("template")

                    # Extract variables from template (allow dotted names)
                    variables = []
                    if isinstance(template, str):
                        import re
                        variables = re.findall(r"\{\{\s*([a-zA-Z0-9_\.]+)", template)
                        variables = list(set(variables))

                    # Extract declared metadata
                    required_variables = []
                    output_schema = None
                    if isinstance(entry, dict):
                        required_variables = entry.get("required_variables", []) or []
                        output_schema = entry.get("output_schema")

                    return {
                        "domain": domain,
                        "version": _VERSION,
                        "file_path": str(yaml_file.relative_to(_PROMPTS_DIR)),
                        "variables": variables,
                        "required_variables": required_variables,
                        "output_schema": output_schema,
                    }
            except Exception:
                pass

    # Check legacy file (legacy prompts have no metadata)
    if name in _load_legacy_prompts():
        return {
            "domain": "legacy",
            "version": "legacy",
            "file_path": "prompts.yaml",
            "variables": [],
            "required_variables": [],
            "output_schema": None,
        }

    raise KeyError(f"Prompt '{name}' not found")


def extract_template_variables(template: str) -> set[str]:
    """
    Extract all variable names used in a Jinja2 template.

    Args:
        template: The template string

    Returns:
        Set of variable names (base variables only, not dotted access)
    """
    import re

    variables = set()

    # Match {{ variable }} patterns (with optional filters/attributes)
    # Captures: {{ name }}, {{ name | filter }}, {{ name.attr }}
    var_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)"
    for match in re.finditer(var_pattern, template):
        variables.add(match.group(1))

    # Match {% if/for variable %} patterns
    control_pattern = r"\{%\s*(?:if|for|elif)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    for match in re.finditer(control_pattern, template):
        variables.add(match.group(1))

    return variables


def check_required_variables(name: str, context: dict[str, Any]) -> list[str]:
    """
    Check if all required variables are provided in the context.

    Args:
        name: The prompt name
        context: The context dict to check

    Returns:
        List of missing variable names (empty if all present)
    """
    try:
        meta = get_prompt_metadata(name)
    except KeyError:
        return []

    # Check declared required_variables first
    required = meta.get("required_variables", [])
    if required:
        return [v for v in required if v not in context]

    # Fall back to extracting from template
    template = get_prompt(name)
    variables = extract_template_variables(template)

    # Filter out shared prompts that are auto-included
    auto_included = {"system_prompt_json", "global_constraints"}
    variables = variables - auto_included

    return [v for v in variables if v not in context]


def validate_all_prompts() -> dict[str, list[str]]:
    """
    Validate all prompts for Jinja2 syntax errors.

    Returns:
        Dict mapping prompt names to list of errors (empty list if valid)
    """
    results: dict[str, list[str]] = {}
    prompts = _load_prompts()

    for name, value in prompts.items():
        errors = []
        template = None

        if isinstance(value, str):
            template = value
        elif isinstance(value, dict) and "template" in value:
            template = value["template"]

        if template:
            try:
                _jinja_env().parse(template)
            except Exception as e:
                errors.append(f"Jinja2 syntax error: {e}")

        results[name] = errors

    return results


def get_prompt_info(name: str) -> dict[str, Any]:
    """
    Get comprehensive information about a prompt for debugging/documentation.

    Args:
        name: The prompt name

    Returns:
        Dict with template, variables, metadata, and validation status
    """
    try:
        template = get_prompt(name)
        meta = get_prompt_metadata(name)
        variables = extract_template_variables(template)

        # Check for syntax errors
        syntax_valid = True
        syntax_error = None
        try:
            _jinja_env().parse(template)
        except Exception as e:
            syntax_valid = False
            syntax_error = str(e)

        return {
            "name": name,
            "domain": meta.get("domain"),
            "version": meta.get("version"),
            "file_path": meta.get("file_path"),
            "template_length": len(template),
            "variables": sorted(variables),
            "required_variables": meta.get("required_variables", []),
            "output_schema": meta.get("output_schema"),
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
        }
    except KeyError as e:
        return {"name": name, "error": str(e)}


def validate_prompt_output(name: str, output: dict) -> bool:
    """
    Validate a prompt output dict against a minimal output schema declared in
    the prompt metadata. This is intentionally lightweight: it verifies the
    presence of required top-level keys when `output_schema` contains a
    `required` list (as in JSON Schema).

    Args:
        name: Prompt key
        output: The parsed output object (dict)

    Returns:
        True if validation passes.

    Raises:
        KeyError: If prompt is not found or has no schema
        ValueError: If validation fails
    """
    meta = get_prompt_metadata(name)
    schema = meta.get("output_schema")
    if not schema:
        raise KeyError(f"No output_schema declared for prompt '{name}'")

    # Support simple JSON-schema like `required` property
    required = schema.get("required") if isinstance(schema, dict) else None
    if required and isinstance(required, list):
        missing = [k for k in required if k not in output]
        if missing:
            raise ValueError(f"Missing required keys in output: {missing}")
    return True


def clear_cache() -> None:
    """Clear all cached prompts (useful for hot-reload scenarios)."""
    _load_legacy_prompts.cache_clear()
    _load_versioned_prompts.cache_clear()
    _load_prompts.cache_clear()
    _jinja_env.cache_clear()
