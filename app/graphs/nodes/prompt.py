import logging
import uuid

from sqlalchemy.orm import Session

from app.config.loaders import load_grammar_to_prompt_mapping_v1
from app.db.models import Scene
from app.services.artifacts import ArtifactService
from .constants import ARTIFACT_LAYOUT_TEMPLATE, ARTIFACT_PANEL_SEMANTICS, ARTIFACT_RENDER_SPEC


logger = logging.getLogger(__name__)


def compute_prompt_compiler(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str = "default",
    story_style_id: str | None = None,
    image_style_id: str | None = None,
) -> dict:
    mapping = load_grammar_to_prompt_mapping_v1().mapping

    panels = panel_semantics.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_semantics.panels must be a non-empty list")

    image_style_id = image_style_id or style_id or "default"

    parts: list[str] = []
    parts.append(f"STYLE: {image_style_id}")
    if story_style_id:
        parts.append(f"STORY_STYLE: {story_style_id}")
    if image_style_id:
        parts.append(f"IMAGE_STYLE: {image_style_id}")

    template_id = layout_template.get("template_id")
    if template_id:
        parts.append(f"LAYOUT_TEMPLATE: {template_id}")

    for idx, panel in enumerate(panels, start=1):
        grammar_id = panel.get("grammar_id")
        semantic_text = panel.get("text")

        mapped = mapping.get(grammar_id, "") if isinstance(grammar_id, str) else ""
        line = f"PANEL {idx}: {mapped}".strip()
        if semantic_text:
            line = f"{line} | {semantic_text}" if line else str(semantic_text)
        parts.append(line)

    prompt = "\n".join([p for p in parts if p])
    return {
        "style_id": image_style_id,
        "story_style_id": story_style_id,
        "image_style_id": image_style_id,
        "prompt": prompt,
    }


def run_prompt_compiler(db: Session, scene_id: uuid.UUID, style_id: str = "default"):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    svc = ArtifactService(db)
    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
    if layout is None:
        raise ValueError("layout_template artifact not found")

    story_style_id = "default"
    image_style_id = "default"
    if scene.story is not None:
        story_style_id = scene.story.default_story_style or "default"
        image_style_id = scene.story.default_image_style or "default"

    if scene.story_style_override:
        story_style_id = scene.story_style_override
    if scene.image_style_override:
        image_style_id = scene.image_style_override

    if style_id:
        image_style_id = style_id

    payload = compute_prompt_compiler(
        panel_semantics=semantics.payload,
        layout_template=layout.payload,
        style_id=image_style_id,
        story_style_id=story_style_id,
        image_style_id=image_style_id,
    )
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_SPEC, payload=payload)
    logger.info(
        "node_complete node_name=PromptCompiler scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact
