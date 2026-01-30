from app.prompts import loader


def test_character_style_map_contains_variants():
    data = loader.get_prompt_data("character_style_map")
    assert "ethnicities" in data
    assert any(e["id"] == "east_asian" for e in data["ethnicities"])
    assert "body_types" in data
    assert any(bt["id"] == "curvy" for bt in data["body_types"])
    assert "distinctive_features" in data
    assert any(df["id"] == "glasses" for df in data["distinctive_features"])
    assert "art_style_presets" in data
    assert any(a["id"] == "soft_webtoon" for a in data["art_style_presets"])


def test_preserves_backward_compatibility():
    # Existing per-gender templates should still be available as strings
    data = loader.get_prompt_data("character_style_map")
    assert isinstance(data["male"]["teen"], str)
    assert "flower-boy" in data["male"]["teen"] or "flower-boy aesthetic" in data["male"]["teen"]
