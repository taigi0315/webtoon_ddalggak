import shutil
from pathlib import Path
import pytest

from app.prompts import loader


def test_list_prompts_domain():
    names = loader.list_prompts(domain="scene_planning")
    assert "prompt_scene_intent" in names


def test_get_prompt_metadata_variables():
    meta = loader.get_prompt_metadata("prompt_scene_intent")
    vars_ = set(meta["variables"])
    # Should include variables referenced in the template
    assert "scene_text" in vars_
    assert "char_list" in vars_


def test_render_prompt_includes_shared():
    # Do not pass global_constraints; render_prompt should auto-include it
    rendered = loader.render_prompt(
        "prompt_scene_intent",
        scene_text="A brief scene",
        char_list="[]",
    )
    assert "Constraints:" in rendered


def test_invalid_template_raises_and_is_not_silently_ignored(tmp_path, monkeypatch):
    # Create a bad template file inside v1/utility
    prompts_dir = Path(loader.__file__).resolve().parent
    target_dir = prompts_dir / "v1" / "utility"
    target_dir.mkdir(parents=True, exist_ok=True)
    bad_file = target_dir / "bad_template_for_test.yaml"
    bad_file.write_text("bad_prompt: '{% if foo %} missing endif'\n")

    try:
        # Clear caches so loader picks up new file
        loader.clear_cache()
        with pytest.raises(ValueError):
            loader._load_versioned_prompts()
    finally:
        # Cleanup
        bad_file.unlink()
        loader.clear_cache()
