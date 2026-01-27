import pytest


@pytest.mark.anyio
async def test_list_styles(client):
    story_styles = (await client.get("/v1/styles/story")).json()
    image_styles = (await client.get("/v1/styles/image")).json()

    assert any(item["id"] == "default" for item in story_styles)
    assert any(item["id"] == "default" for item in image_styles)


@pytest.mark.anyio
async def test_scene_set_style(client):
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

    updated = (
        await client.post(
            f"/v1/scenes/{scene['scene_id']}/set-style",
            json={"story_style_id": "romance", "image_style_id": "soft_webtoon"},
        )
    ).json()

    assert updated["story_style_override"] == "romance"
    assert updated["image_style_override"] == "soft_webtoon"


@pytest.mark.anyio
async def test_story_set_style_defaults(client):
    project = (await client.post("/v1/projects", json={"name": "p"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s"},
        )
    ).json()

    updated = (
        await client.post(
            f"/v1/stories/{story['story_id']}/set-style-defaults",
            json={"default_story_style": "comedy", "default_image_style": "soft_webtoon"},
        )
    ).json()

    assert updated["default_story_style"] == "comedy"
    assert updated["default_image_style"] == "soft_webtoon"
