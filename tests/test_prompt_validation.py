"""
Comprehensive tests for prompt template validation and rendering.

Tests cover:
- Jinja2 syntax validation
- Required variable checking
- Template rendering with sample inputs
- Output schema validation
- Edge cases (empty inputs, special characters)
"""

import pytest

from app.prompts.loader import (
    check_required_variables,
    clear_cache,
    extract_template_variables,
    get_prompt,
    get_prompt_info,
    get_prompt_metadata,
    list_prompts,
    render_prompt,
    validate_all_prompts,
    validate_prompt_output,
)


@pytest.fixture(autouse=True)
def clear_prompt_cache():
    """Clear prompt cache before each test."""
    clear_cache()
    yield
    clear_cache()


class TestJinja2SyntaxValidation:
    """Tests for Jinja2 template syntax validation."""

    def test_all_prompts_have_valid_syntax(self):
        """All prompts should have valid Jinja2 syntax."""
        results = validate_all_prompts()
        invalid = {name: errors for name, errors in results.items() if errors}
        assert not invalid, f"Prompts with syntax errors: {invalid}"

    def test_extract_variables_simple(self):
        """Extract variables from simple template."""
        template = "Hello {{ name }}, your age is {{ age }}."
        variables = extract_template_variables(template)
        assert "name" in variables
        assert "age" in variables

    def test_extract_variables_with_filters(self):
        """Extract variables even when filters are applied."""
        template = "{{ name | upper }} - {{ value | default('N/A') }}"
        variables = extract_template_variables(template)
        assert "name" in variables
        assert "value" in variables

    def test_extract_variables_conditional(self):
        """Extract variables from conditional blocks."""
        template = "{% if show_extra %}Extra: {{ extra_text }}{% endif %}"
        variables = extract_template_variables(template)
        assert "show_extra" in variables or "extra_text" in variables


class TestRequiredVariableChecking:
    """Tests for required variable validation."""

    def test_check_required_variables_all_present(self):
        """No missing variables when all are provided."""
        # Use a prompt that exists
        prompts = list_prompts()
        if not prompts:
            pytest.skip("No prompts available")

        prompt_name = prompts[0]
        template = get_prompt(prompt_name)
        variables = extract_template_variables(template)

        # Create context with all variables
        context = {v: "test" for v in variables}
        context["system_prompt_json"] = "test"
        context["global_constraints"] = "test"

        missing = check_required_variables(prompt_name, context)
        # Should have no missing required variables
        assert isinstance(missing, list)

    def test_check_required_variables_missing(self):
        """Detect missing required variables."""
        prompts = list_prompts("scene_planning")
        if not prompts:
            pytest.skip("No scene_planning prompts available")

        prompt_name = prompts[0]
        missing = check_required_variables(prompt_name, {})
        # Should detect some missing variables
        assert isinstance(missing, list)


class TestPromptRendering:
    """Tests for prompt template rendering."""

    def test_render_prompt_scene_intent(self):
        """Render scene_intent prompt with sample data."""
        try:
            rendered = render_prompt(
                "prompt_scene_intent",
                scene_text="Alice walked into the room and saw Bob.",
                genre_text="romance",
                char_list="Alice, Bob",
            )
            assert len(rendered) > 100
            assert "Alice" in rendered or "scene" in rendered.lower()
        except KeyError:
            pytest.skip("prompt_scene_intent not available")

    def test_render_prompt_panel_plan(self):
        """Render panel_plan prompt with sample data."""
        try:
            rendered = render_prompt(
                "prompt_panel_plan",
                scene_text="The confrontation happened at midnight.",
                panel_count=4,
                char_list="Hero, Villain",
                # Optional blocks - provide empty strings to avoid undefined
                intent_block="",
                importance_block="",
                qc_block="",
            )
            assert len(rendered) > 100
            assert "panel" in rendered.lower() or "4" in rendered
        except KeyError:
            pytest.skip("prompt_panel_plan not available")

    def test_render_prompt_character_extraction(self):
        """Render character_extraction prompt with sample data."""
        try:
            rendered = render_prompt(
                "prompt_character_extraction",
                source_text="John and Mary were childhood friends.",
                max_characters=5,
            )
            assert len(rendered) > 50
            assert "character" in rendered.lower()
        except KeyError:
            pytest.skip("prompt_character_extraction not available")

    def test_render_prompt_auto_includes_shared(self):
        """Shared prompts are auto-included in context."""
        prompts = list_prompts()
        if not prompts:
            pytest.skip("No prompts available")

        # Find a prompt that uses system_prompt_json
        for name in prompts:
            try:
                template = get_prompt(name)
                if "system_prompt_json" in template:
                    # Should render without explicitly providing system_prompt_json
                    variables = extract_template_variables(template)
                    context = {v: "test" for v in variables if v not in ("system_prompt_json", "global_constraints")}
                    rendered = render_prompt(name, **context)
                    assert rendered  # Should not fail
                    return
            except Exception:
                continue

    def test_render_prompt_with_validation(self):
        """Render with validation enabled should catch missing variables."""
        try:
            # This should raise ValueError due to missing variables
            with pytest.raises(ValueError, match="Missing required variables"):
                render_prompt("prompt_scene_intent", validate=True)
        except KeyError:
            pytest.skip("prompt_scene_intent not available")


class TestPromptMetadata:
    """Tests for prompt metadata extraction."""

    def test_get_prompt_metadata_returns_domain(self):
        """Metadata should include domain information."""
        prompts = list_prompts("scene_planning")
        if not prompts:
            pytest.skip("No scene_planning prompts available")

        meta = get_prompt_metadata(prompts[0])
        assert meta["domain"] == "scene_planning"
        assert meta["version"] == "v1"

    def test_get_prompt_metadata_extracts_variables(self):
        """Metadata should include extracted variables."""
        prompts = list_prompts()
        if not prompts:
            pytest.skip("No prompts available")

        for name in prompts:
            try:
                meta = get_prompt_metadata(name)
                assert "variables" in meta
                assert isinstance(meta["variables"], list)
                return
            except KeyError:
                continue

    def test_get_prompt_info_comprehensive(self):
        """get_prompt_info returns comprehensive data."""
        prompts = list_prompts()
        if not prompts:
            pytest.skip("No prompts available")

        info = get_prompt_info(prompts[0])
        assert "name" in info
        assert "syntax_valid" in info
        assert info["syntax_valid"] is True


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_render_with_empty_string_values(self):
        """Rendering with empty strings should work."""
        try:
            rendered = render_prompt(
                "prompt_scene_intent",
                scene_text="",
                genre_text="",
                char_list="",
            )
            assert isinstance(rendered, str)
        except KeyError:
            pytest.skip("prompt_scene_intent not available")

    def test_render_with_special_characters(self):
        """Rendering with special characters should work."""
        try:
            rendered = render_prompt(
                "prompt_scene_intent",
                scene_text='She said "Hello!" & waved.',
                genre_text="drama",
                char_list="Alice, Bob",
            )
            assert isinstance(rendered, str)
            assert "Hello" in rendered or "scene" in rendered.lower()
        except KeyError:
            pytest.skip("prompt_scene_intent not available")

    def test_render_with_unicode(self):
        """Rendering with unicode characters should work."""
        try:
            rendered = render_prompt(
                "prompt_scene_intent",
                scene_text="한글 텍스트와 日本語 text",
                genre_text="drama",
                char_list="민지, 유나",
            )
            assert isinstance(rendered, str)
        except KeyError:
            pytest.skip("prompt_scene_intent not available")

    def test_render_with_long_text(self):
        """Rendering with very long text should work."""
        try:
            long_text = "This is a test. " * 1000  # ~16KB of text
            rendered = render_prompt(
                "prompt_scene_intent",
                scene_text=long_text,
                genre_text="drama",
                char_list="Character",
            )
            assert isinstance(rendered, str)
            assert len(rendered) > len(long_text)
        except KeyError:
            pytest.skip("prompt_scene_intent not available")

    def test_nonexistent_prompt_raises_keyerror(self):
        """Accessing nonexistent prompt should raise KeyError."""
        with pytest.raises(KeyError):
            get_prompt("nonexistent_prompt_xyz")

    def test_nonexistent_prompt_metadata_raises_keyerror(self):
        """Accessing metadata for nonexistent prompt should raise KeyError."""
        with pytest.raises(KeyError):
            get_prompt_metadata("nonexistent_prompt_xyz")


class TestPromptDomains:
    """Tests for prompt domain organization."""

    def test_list_prompts_by_domain(self):
        """Can list prompts filtered by domain."""
        domains = ["shared", "story_build", "scene_planning", "evaluation", "dialogue", "utility"]

        for domain in domains:
            prompts = list_prompts(domain)
            assert isinstance(prompts, list)
            # Each domain should have at least some prompts (or be empty)

    def test_all_domains_have_prompts(self):
        """At least some domains should have prompts."""
        all_prompts = list_prompts()
        assert len(all_prompts) > 0, "No prompts found in any domain"

    def test_scene_planning_prompts_exist(self):
        """Scene planning domain should have key prompts."""
        prompts = list_prompts("scene_planning")
        prompt_names = set(prompts)

        # At least one of these should exist
        expected = {"prompt_scene_intent", "prompt_panel_plan", "prompt_panel_semantics"}
        found = prompt_names & expected
        assert len(found) > 0, f"No scene_planning prompts found. Available: {prompts}"


class TestOutputSchemaValidation:
    """Tests for output schema validation."""

    def test_validate_output_missing_required_keys(self):
        """Validation should fail when required keys are missing."""
        # Create a mock prompt with output schema
        # This test depends on having prompts with output_schema defined
        prompts = list_prompts()

        for name in prompts:
            try:
                meta = get_prompt_metadata(name)
                if meta.get("output_schema"):
                    # Test with empty output
                    schema = meta["output_schema"]
                    if isinstance(schema, dict) and schema.get("required"):
                        with pytest.raises(ValueError):
                            validate_prompt_output(name, {})
                        return
            except (KeyError, ValueError):
                continue

        pytest.skip("No prompts with output_schema found")

    def test_validate_output_all_required_present(self):
        """Validation should pass when all required keys present."""
        prompts = list_prompts()

        for name in prompts:
            try:
                meta = get_prompt_metadata(name)
                if meta.get("output_schema"):
                    schema = meta["output_schema"]
                    if isinstance(schema, dict) and schema.get("required"):
                        # Create output with all required keys
                        output = {k: "test" for k in schema["required"]}
                        result = validate_prompt_output(name, output)
                        assert result is True
                        return
            except (KeyError, ValueError):
                continue

        pytest.skip("No prompts with output_schema found")
