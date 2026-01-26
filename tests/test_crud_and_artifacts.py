import uuid

import pytest

from app.db.session import get_sessionmaker
from app.services.artifacts import ArtifactService


@pytest.mark.anyio
async def test_project_story_scene_and_artifacts(client):
    project = (await client.post("/v1/projects", json={"name": "p1"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s1"},
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
        service = ArtifactService(db)
        a1 = service.create_artifact(scene_id=scene_id, type="scene_intent", payload={"a": 1})
        a2 = service.create_artifact(scene_id=scene_id, type="scene_intent", payload={"a": 2})
        a3 = service.create_artifact(scene_id=scene_id, type="scene_intent", payload={"a": 3})

        assert a1.version == 1
        assert a2.version == 2
        assert a3.version == 3
        assert a2.parent_id == a1.artifact_id
        assert a3.parent_id == a2.artifact_id

    resp = await client.get(
        f"/v1/scenes/{scene['scene_id']}/artifacts",
        params={"type": "scene_intent"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert [it["version"] for it in items] == [1, 2, 3]

    artifact_id = items[0]["artifact_id"]
    resp = await client.get(f"/v1/artifacts/{artifact_id}")
    assert resp.status_code == 200
    assert resp.json()["artifact_id"] == artifact_id
