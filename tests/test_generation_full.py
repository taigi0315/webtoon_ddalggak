import json
import uuid

import pytest

from app.core import settings as settings_module
from app.graphs import nodes


@pytest.mark.anyio
async def test_generate_full_pipeline_mocked(client, monkeypatch, tmp_path):
    settings_module.settings.media_root = str(tmp_path / "media")

    class FakeGemini:
        def generate_text(self, prompt: str, model=None) -> str:
            if "Extract scene intent" in prompt:
                return json.dumps({"summary": "sum", "mood": "m", "beats": ["b1"]})
            if "Generate a panel plan" in prompt:
                return json.dumps(
                    {
                        "panels": [
                            {"grammar_id": "establishing", "story_function": "setup"},
                            {"grammar_id": "reaction", "story_function": "beat"},
                            {"grammar_id": "dialogue_medium", "story_function": "talk"},
                        ]
                    }
                )
            if "Fill panel semantics" in prompt:
                return json.dumps(
                    {
                        "panels": [
                            {"grammar_id": "establishing", "text": "wide street"},
                            {"grammar_id": "reaction", "text": "shock"},
                            {"grammar_id": "dialogue_medium", "text": "talking"},
                        ]
                    }
                )
            if "Evaluate whether the panel semantics" in prompt:
                return json.dumps({"coherence_score": 8, "faithfulness_score": 7, "notes": "ok"})
            return json.dumps({})

        def generate_image(self, prompt: str, model=None):
            return b"fakebytes", "image/png"

    monkeypatch.setattr(nodes, "_build_gemini_client", lambda: FakeGemini())

    project = (await client.post("/v1/projects", json={"name": "p"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s"},
        )
    ).json()
    scene = (
        await client.post(
            f"/v1/stories/{story['story_id']}/scenes",
            json={"source_text": "hello"},
        )
    ).json()

    scene_id = uuid.UUID(scene["scene_id"])

    resp = await client.post(
        f"/v1/scenes/{scene_id}/generate/full",
        json={"panel_count": 3, "style_id": "default"},
    )
    assert resp.status_code == 200
    body = resp.json()

    for key in [
        "scene_intent_artifact_id",
        "panel_plan_artifact_id",
        "panel_plan_normalized_artifact_id",
        "layout_template_artifact_id",
        "panel_semantics_artifact_id",
        "render_spec_artifact_id",
        "render_result_artifact_id",
        "blind_test_report_artifact_id",
    ]:
        assert key in body
        uuid.UUID(body[key])
