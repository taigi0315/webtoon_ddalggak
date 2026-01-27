import pytest


@pytest.mark.anyio
async def test_environment_anchor_crud(client):
    create = await client.post(
        "/v1/environments",
        json={"description": "A cozy cafe with warm lights", "pinned": True},
    )
    assert create.status_code == 200
    env = create.json()
    assert env["anchor_type"] == "descriptive"
    assert env["pinned"] is True

    get_resp = await client.get(f"/v1/environments/{env['environment_id']}")
    assert get_resp.status_code == 200

    promote = await client.post(
        f"/v1/environments/{env['environment_id']}/promote",
        json={
            "reference_images": [{"image_url": "https://example.com/bg.png"}],
            "locked_elements": [{"element": "barista_counter"}],
        },
    )
    assert promote.status_code == 200
    promoted = promote.json()
    assert promoted["anchor_type"] == "visual"
    assert promoted["usage_count"] == 1

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
            json={"source_text": "hello", "environment_id": env["environment_id"]},
        )
    ).json()
    assert scene["environment_id"] == env["environment_id"]

    cleared = (
        await client.post(
            f"/v1/scenes/{scene['scene_id']}/set-environment",
            json={"environment_id": None},
        )
    ).json()
    assert cleared["environment_id"] is None
