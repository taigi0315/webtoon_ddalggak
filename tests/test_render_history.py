import uuid

import pytest

from app.db.session import get_sessionmaker
from app.graphs import nodes
from app.services.artifacts import ArtifactService


@pytest.mark.anyio
async def test_list_scene_renders(client):
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

    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        svc = ArtifactService(db)
        svc.create_artifact(
            scene_id=scene_id,
            type=nodes.ARTIFACT_RENDER_RESULT,
            payload={"image_url": "a", "mime_type": "image/png"},
        )
        svc.create_artifact(
            scene_id=scene_id,
            type=nodes.ARTIFACT_RENDER_RESULT,
            payload={"image_url": "b", "mime_type": "image/png"},
        )

    resp = await client.get(f"/v1/scenes/{scene_id}/renders")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert items[0]["type"] == nodes.ARTIFACT_RENDER_RESULT
