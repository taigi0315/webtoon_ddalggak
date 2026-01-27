import uuid

import pytest


@pytest.mark.anyio
async def test_dialogue_layer_crud(client):
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

    scene_id = scene["scene_id"]
    bubble_id = str(uuid.uuid4())

    create = await client.post(
        f"/v1/scenes/{scene_id}/dialogue",
        json={
            "bubbles": [
                {
                    "bubble_id": bubble_id,
                    "panel_id": 1,
                    "text": "Hi!",
                    "position": {"x": 0.5, "y": 0.2},
                    "size": {"w": 0.2, "h": 0.1},
                    "tail": {"x": 0.48, "y": 0.32},
                }
            ]
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["scene_id"] == scene_id
    assert body["bubbles"][0]["bubble_id"] == bubble_id

    get_resp = await client.get(f"/v1/scenes/{scene_id}/dialogue")
    assert get_resp.status_code == 200

    update = await client.put(
        f"/v1/dialogue/{body['dialogue_id']}",
        json={
            "bubbles": [
                {
                    "bubble_id": bubble_id,
                    "panel_id": 1,
                    "text": "Hello!",
                    "position": {"x": 0.4, "y": 0.25},
                    "size": {"w": 0.25, "h": 0.12},
                }
            ]
        },
    )
    assert update.status_code == 200
    assert update.json()["bubbles"][0]["text"] == "Hello!"
