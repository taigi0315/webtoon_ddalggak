import uuid

import pytest


@pytest.mark.anyio
async def test_layers_crud(client):
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

    layer_id = None
    obj_id = str(uuid.uuid4())

    create = await client.post(
        f"/v1/scenes/{scene['scene_id']}/layers",
        json={
            "layer_type": "dialogue",
            "objects": [
                {
                    "id": obj_id,
                    "panel_id": 1,
                    "type": "speech_bubble",
                    "text": "Hi",
                    "geometry": {"x": 0.5, "y": 0.2, "w": 0.3, "h": 0.12},
                    "tail": {"x": 0.52, "y": 0.34},
                    "z_index": 1,
                }
            ],
        },
    )
    assert create.status_code == 200
    layer = create.json()
    layer_id = layer["layer_id"]

    items = (await client.get(f"/v1/scenes/{scene['scene_id']}/layers")).json()
    assert len(items) == 1
    assert items[0]["objects"][0]["id"] == obj_id

    update = await client.put(
        f"/v1/layers/{layer_id}",
        json={
            "objects": [
                {
                    "id": obj_id,
                    "panel_id": 1,
                    "type": "speech_bubble",
                    "text": "Hello",
                    "geometry": {"x": 0.4, "y": 0.25, "w": 0.3, "h": 0.12},
                    "z_index": 2,
                }
            ]
        },
    )
    assert update.status_code == 200
    assert update.json()["objects"][0]["text"] == "Hello"
