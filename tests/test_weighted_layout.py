import uuid

from app.db.session import get_sessionmaker
from app.graphs import nodes
from app.services.artifacts import ArtifactService


import pytest

@pytest.mark.anyio
async def test_run_panel_plan_assigns_weights(client):
    # Create a scene
    project = (await client.post("/v1/projects", json={"name": "p"})).json()
    story = (await client.post(f"/v1/projects/{project['project_id']}/stories", json={"title": "s"})).json()
    scene = (await client.post(f"/v1/stories/{story['story_id']}/scenes", json={"source_text": "He revealed the secret. It was a shock."})).json()
    scene_id = uuid.UUID(scene["scene_id"])

    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        svc = ArtifactService(db)
        # Generate panel plan (1-4 panels default)
        artifact = nodes.run_panel_plan_generator(db, scene_id, panel_count=3)
        assert artifact.type == nodes.ARTIFACT_PANEL_PLAN
        plan = artifact.payload
        assert "panels" in plan
        for p in plan["panels"]:
            assert "weight" in p
            assert 0.1 <= float(p["weight"]) <= 1.0


@pytest.mark.anyio
async def test_weighted_layout_resolver_applies_heights(client):
    project = (await client.post("/v1/projects", json={"name": "p2"})).json()
    story = (await client.post(f"/v1/projects/{project['project_id']}/stories", json={"title": "s2"})).json()
    scene = (await client.post(f"/v1/stories/{story['story_id']}/scenes", json={"source_text": "A short scene."})).json()
    scene_id = uuid.UUID(scene["scene_id"])

    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        svc = ArtifactService(db)
        # Create a panel plan with two panels and explicit weights
        panel_plan = {"panels": [{"panel_index": 1, "grammar_id": "establishing", "weight": 0.8}, {"panel_index": 2, "grammar_id": "reaction", "weight": 0.2}]}
        svc.create_artifact(scene_id=scene_id, type=nodes.ARTIFACT_PANEL_PLAN, payload=panel_plan)

        layout_artifact = nodes.run_layout_template_resolver(db, scene_id)
        assert layout_artifact.type == nodes.ARTIFACT_LAYOUT_TEMPLATE
        panels = layout_artifact.payload.get("panels", [])
        assert len(panels) == 2
        # Heights should reflect weights roughly (first > second)
        h1 = panels[0]["h"]
        h2 = panels[1]["h"]
        assert h1 > h2
