import pytest


@pytest.mark.anyio
async def test_character_refs_and_approval_flow(client):
    project = (await client.post("/v1/projects", json={"name": "p1"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s1"},
        )
    ).json()

    character = (
        await client.post(
            f"/v1/stories/{story['story_id']}/characters",
            json={
                "name": "Hero",
                "description": "Main hero",
                "role": "main",
                "identity_line": "A brave hero with a scar.",
            },
        )
    ).json()

    # Main characters cannot be approved without at least one approved face ref
    resp = await client.post(f"/v1/characters/{character['character_id']}/approve")
    assert resp.status_code == 400

    ref = (
        await client.post(
            f"/v1/characters/{character['character_id']}/refs",
            json={"image_url": "/media/hero_face.png", "ref_type": "face"},
        )
    ).json()

    # Approve the reference image
    resp = await client.post(
        f"/v1/characters/{character['character_id']}/approve-ref",
        json={"reference_image_id": ref["reference_image_id"]},
    )
    assert resp.status_code == 200
    approved_ref = resp.json()
    assert approved_ref["approved"] is True

    # Set it as primary
    resp = await client.post(
        f"/v1/characters/{character['character_id']}/set-primary-ref",
        json={"reference_image_id": ref["reference_image_id"]},
    )
    assert resp.status_code == 200
    primary_ref = resp.json()
    assert primary_ref["is_primary"] is True

    # Now character approval should succeed
    resp = await client.post(f"/v1/characters/{character['character_id']}/approve")
    assert resp.status_code == 200
    approved_character = resp.json()
    assert approved_character["approved"] is True

    # Listing refs should include it
    resp = await client.get(f"/v1/characters/{character['character_id']}/refs")
    assert resp.status_code == 200
    refs = resp.json()
    assert len(refs) == 1
    assert refs[0]["reference_image_id"] == ref["reference_image_id"]
    assert refs[0]["ref_type"] == "face"
    assert refs[0]["approved"] is True
    assert refs[0]["is_primary"] is True
