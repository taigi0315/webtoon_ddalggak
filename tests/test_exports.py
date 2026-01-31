import pytest


@pytest.mark.anyio
async def test_export_stub(client):
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

    export = await client.post(f"/v1/scenes/{scene['scene_id']}/export")
    assert export.status_code == 200
    body = export.json()
    assert body["status"] in {"queued", "succeeded"}

    fetched = await client.get(f"/v1/exports/{body['export_id']}")
    assert fetched.status_code == 200

    not_ready = await client.get(f"/v1/exports/{body['export_id']}/download")
    assert not_ready.status_code in {200, 400}

    episode = (
        await client.post(
            f"/v1/stories/{story['story_id']}/episodes",
            json={"title": "Episode 1", "default_image_style": "default"},
        )
    ).json()

    ep_export = await client.post(f"/v1/episodes/{episode['episode_id']}/export")
    assert ep_export.status_code == 200
    assert ep_export.json()["episode_id"] == episode["episode_id"]

    ep_download = await client.get(f"/v1/exports/{ep_export.json()['export_id']}/download")
    assert ep_download.status_code in {200, 400}

    finalize = await client.post(f"/v1/exports/{ep_export.json()['export_id']}/finalize")
    assert finalize.status_code in {200, 400}
