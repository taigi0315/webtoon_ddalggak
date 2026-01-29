from app.graphs.nodes.utils import _derive_panel_plan_features


def test_derive_panel_plan_features_basic():
    panel_plan = {"panels": [{"weight": 0.8}, {"weight": 0.2}], "must_show": ["Protagonist", "Window"]}
    features = _derive_panel_plan_features(panel_plan, character_names=["Protagonist"])
    assert features["panel_count"] == 2
    assert features["max_weight"] == 0.8
    assert features["avg_weight"] == 0.5
    assert features["num_large"] == 1
    assert features["has_strong_panel"] is True
    assert features["hero_count"] >= 1
