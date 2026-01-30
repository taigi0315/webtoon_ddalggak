import uuid

from app.graphs import story_build, nodes


class FakeArtifact:
    def __init__(self, aid: uuid.UUID, payload: dict):
        self.artifact_id = aid
        self.payload = payload


def test_no_more_than_two_consecutive_templates(monkeypatch, tmp_path):
    # Create three fake scenes
    scene_ids = [str(uuid.uuid4()) for _ in range(3)]

    # Monkeypatch nodes functions used in per-scene loop
    def fake_run_scene_intent_extractor(db, scene_uuid, gemini=None):
        return FakeArtifact(uuid.uuid4(), {})

    def fake_run_panel_plan_generator(db, scene_uuid, panel_count=3, gemini=None):
        return FakeArtifact(uuid.uuid4(), {"panels": [{}, {}]})

    def fake_run_panel_plan_normalizer(db, scene_uuid):
        return FakeArtifact(uuid.uuid4(), {})

    # Simulate layout resolver that returns the same template unless excluded
    def fake_run_layout_template_resolver(db, scene_uuid, excluded_template_ids=None):
        if excluded_template_ids and "9x16_3_vertical" in excluded_template_ids:
            return FakeArtifact(uuid.uuid4(), {"template_id": "9x16_2_asym"})
        return FakeArtifact(uuid.uuid4(), {"template_id": "9x16_3_vertical"})

    def fake_run_panel_semantic_filler(db, scene_uuid, gemini=None):
        return FakeArtifact(uuid.uuid4(), {})

    def fake_run_qc_checker(db, scene_uuid):
        return FakeArtifact(uuid.uuid4(), {})

    def fake_run_dialogue_extractor(db, scene_uuid):
        return FakeArtifact(uuid.uuid4(), {})

    monkeypatch.setattr(nodes, "run_scene_intent_extractor", fake_run_scene_intent_extractor)
    monkeypatch.setattr(nodes, "run_panel_plan_generator", fake_run_panel_plan_generator)
    monkeypatch.setattr(nodes, "run_panel_plan_normalizer", fake_run_panel_plan_normalizer)
    monkeypatch.setattr(nodes, "run_layout_template_resolver", fake_run_layout_template_resolver)
    monkeypatch.setattr(nodes, "run_panel_semantic_filler", fake_run_panel_semantic_filler)
    monkeypatch.setattr(nodes, "run_qc_checker", fake_run_qc_checker)
    monkeypatch.setattr(nodes, "run_dialogue_extractor", fake_run_dialogue_extractor)

    state = {"scene_ids": scene_ids}

    # Call the per-scene planning loop directly
    result = story_build._node_per_scene_planning_loop(state, gemini=None)
    planning_artifacts = result.get("planning_artifact_ids", [])

    # Ensure that layout resolver was asked to re-resolve for the 3rd scene (i.e., no 3-in-a-row identical)
    assert len(planning_artifacts) == 3
