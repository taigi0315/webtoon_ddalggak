import pytest


@pytest.mark.anyio
async def test_episode_crud(client):
    project = (await client.post("/v1/projects", json={"name": "p"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s"},
        )
    ).json()
    scene1 = (
        await client.post(
            f"/v1/stories/{story['story_id']}/scenes",
            json={"source_text": "one"},
        )
    ).json()
    scene2 = (
        await client.post(
            f"/v1/stories/{story['story_id']}/scenes",
            json={"source_text": "two"},
        )
    ).json()

    episode = (
        await client.post(
            f"/v1/stories/{story['story_id']}/episodes",
            json={"title": "Episode 1", "default_image_style": "default"},
        )
    ).json()

    updated = (
        await client.post(
            f"/v1/episodes/{episode['episode_id']}/scenes",
            json={"scene_ids_ordered": [scene2["scene_id"], scene1["scene_id"]]},
        )
    ).json()
    assert updated["scene_ids_ordered"] == [scene2["scene_id"], scene1["scene_id"]]

    fetched = (await client.get(f"/v1/episodes/{episode['episode_id']}")).json()
    assert fetched["scene_ids_ordered"] == [scene2["scene_id"], scene1["scene_id"]]

    styled = (
        await client.post(
            f"/v1/episodes/{episode['episode_id']}/set-style",
            json={"default_image_style": "soft_webtoon"},
        )
    ).json()
    assert styled["default_image_style"] == "soft_webtoon"

    asset = (
        await client.post(
            f"/v1/episodes/{episode['episode_id']}/assets",
            json={"asset_type": "environment", "asset_id": scene1["scene_id"]},
        )
    ).json()
    assert asset["asset_type"] == "environment"

    assets = (await client.get(f"/v1/episodes/{episode['episode_id']}/assets")).json()
    assert len(assets) == 1

    deleted = await client.delete(f"/v1/episodes/{episode['episode_id']}/assets/{asset['episode_asset_id']}")
    assert deleted.status_code == 200

    plan = await client.post(
        f"/v1/episodes/{episode['episode_id']}/generate/plan",
        json={"style_id": "default"},
    )
    assert plan.status_code == 200
