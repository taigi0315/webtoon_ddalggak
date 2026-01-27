import json
import uuid

import pytest

from app.core import settings as settings_module
from app.graphs import nodes


@pytest.mark.anyio
async def test_planning_lock_reuses_planning_artifacts(client, monkeypatch, tmp_path):
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

    # First run generates planning artifacts
    resp1 = await client.post(
        f"/v1/scenes/{scene_id}/generate/full",
        json={"panel_count": 3, "style_id": "default"},
    )
    assert resp1.status_code == 200

    # Lock planning
    lock_resp = await client.post(
        f"/v1/scenes/{scene_id}/planning/lock",
        json={"locked": True},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["planning_locked"] is True

    # Second run should not create new versions for planning artifacts
    resp2 = await client.post(
        f"/v1/scenes/{scene_id}/generate/full",
        json={"panel_count": 3, "style_id": "default"},
    )
    assert resp2.status_code == 200

    for t in [
        nodes.ARTIFACT_SCENE_INTENT,
        nodes.ARTIFACT_PANEL_PLAN,
        nodes.ARTIFACT_PANEL_PLAN_NORMALIZED,
        nodes.ARTIFACT_LAYOUT_TEMPLATE,
        nodes.ARTIFACT_PANEL_SEMANTICS,
    ]:
        items = (
            await client.get(
                f"/v1/scenes/{scene_id}/artifacts",
                params={"type": t},
            )
        ).json()
        assert len(items) == 1
        assert items[0]["version"] == 1

    # But render_result can be versioned
    render_items = (
        await client.get(
            f"/v1/scenes/{scene_id}/artifacts",
            params={"type": nodes.ARTIFACT_RENDER_RESULT},
        )
    ).json()
    assert len(render_items) == 2
    assert [it["version"] for it in render_items] == [1, 2]
