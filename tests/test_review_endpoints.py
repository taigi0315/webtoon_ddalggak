import json
import uuid

import pytest

from app.core import settings as settings_module
from app.graphs import nodes
from app.services.artifacts import ArtifactService


@pytest.mark.anyio
async def test_review_regenerate_and_approve(client, monkeypatch, tmp_path):
    settings_module.settings.media_root = str(tmp_path / "media")

    class FakeGemini:
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

    # Need a render_spec artifact before regenerate can run.
    from app.db.session import get_sessionmaker

    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        ArtifactService(db).create_artifact(
            scene_id=scene_id,
            type=nodes.ARTIFACT_RENDER_SPEC,
            payload={"prompt": "draw"},
        )

    regen = await client.post(f"/v1/scenes/{scene_id}/review/regenerate")
    assert regen.status_code == 200
    regen_id = uuid.UUID(regen.json()["artifact_id"])

    approve = await client.post(
        f"/v1/scenes/{scene_id}/review/approve",
        json={"artifact_id": str(regen_id)},
    )
    assert approve.status_code == 200
    approved_id = uuid.UUID(approve.json()["artifact_id"])
    assert approved_id != regen_id

    # Latest render_result should have approved=true
    resp = await client.get(
        f"/v1/scenes/{scene_id}/artifacts",
        params={"type": nodes.ARTIFACT_RENDER_RESULT},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert items[-1]["payload"].get("approved") is True
