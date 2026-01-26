import uuid

import pytest

from app.core import settings as settings_module
from app.db.session import get_sessionmaker
from app.graphs import nodes
from app.services.artifacts import ArtifactService


def test_prompt_compiler_deterministic():
    panel_semantics = {
        "panels": [
            {"grammar_id": "establishing", "text": "A rainy street at night."},
            {"grammar_id": "reaction", "text": "Character looks shocked."},
        ]
    }
    layout_template = {"template_id": "9x16_3_vertical"}

    out1 = nodes.compute_prompt_compiler(panel_semantics, layout_template, style_id="v1")
    out2 = nodes.compute_prompt_compiler(panel_semantics, layout_template, style_id="v1")

    assert out1 == out2
    assert "STYLE: v1" in out1["prompt"]


@pytest.mark.anyio
async def test_run_layout_resolver_creates_artifact(client):
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
        svc.create_artifact(scene_id=scene_id, type=nodes.ARTIFACT_PANEL_PLAN, payload={"panels": [{"grammar_id": "establishing"}]})

        layout_artifact = nodes.run_layout_template_resolver(db, scene_id)
        assert layout_artifact.type == nodes.ARTIFACT_LAYOUT_TEMPLATE
        assert layout_artifact.payload["template_id"] == "9x16_1"


@pytest.mark.anyio
async def test_run_image_renderer_mocked(client, tmp_path):
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

    settings_module.settings.media_root = str(tmp_path / "media")

    class FakeGemini:
        def generate_image(self, prompt: str, model=None):
            return b"fakebytes", "image/png"

    scene_id = uuid.UUID(scene["scene_id"])

    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        svc = ArtifactService(db)
        svc.create_artifact(scene_id=scene_id, type=nodes.ARTIFACT_RENDER_SPEC, payload={"prompt": "draw"})

        result = nodes.run_image_renderer(db, scene_id, gemini=FakeGemini())
        assert result.type == nodes.ARTIFACT_RENDER_RESULT
        assert result.payload["image_url"].startswith(settings_module.settings.media_url_prefix)
