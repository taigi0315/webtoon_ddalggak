import { fetchJson } from "@/lib/api/client";
import {
  artifactIdSchema,
  artifactsSchema,
  healthSchema,
  projectSchema,
  projectsSchema,
  scenesSchema,
  storiesSchema,
  sceneSchema,
  storySchema,
  styleItemsSchema
} from "@/lib/api/types";

export async function fetchHealth() {
  const payload = await fetchJson("/health");
  return healthSchema.parse(payload);
}

export async function fetchProjects() {
  const payload = await fetchJson("/v1/projects");
  return projectsSchema.parse(payload);
}

export async function createProject(name: string) {
  const payload = await fetchJson("/v1/projects", {
    method: "POST",
    body: JSON.stringify({ name })
  });
  return projectSchema.parse(payload);
}

export async function deleteProject(projectId: string) {
  await fetchJson(`/v1/projects/${projectId}`, {
    method: "DELETE"
  });
  return null;
}

export async function createStory(params: {
  projectId: string;
  title: string;
  defaultStoryStyle: string;
  defaultImageStyle: string;
}) {
  const payload = await fetchJson(`/v1/projects/${params.projectId}/stories`, {
    method: "POST",
    body: JSON.stringify({
      title: params.title,
      default_story_style: params.defaultStoryStyle,
      default_image_style: params.defaultImageStyle
    })
  });
  return storySchema.parse(payload);
}

export async function fetchStory(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}`);
  return storySchema.parse(payload);
}

export async function fetchStories(projectId: string) {
  const payload = await fetchJson(`/v1/projects/${projectId}/stories`);
  return storiesSchema.parse(payload);
}

export async function createScene(params: {
  storyId: string;
  sourceText: string;
  environmentId?: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/scenes`, {
    method: "POST",
    body: JSON.stringify({
      source_text: params.sourceText,
      environment_id: params.environmentId ?? null
    })
  });
  return sceneSchema.parse(payload);
}

export async function fetchScene(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}`);
  return sceneSchema.parse(payload);
}

export async function fetchSceneArtifacts(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/artifacts`);
  return artifactsSchema.parse(payload);
}

export async function fetchSceneRenders(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/renders`);
  return artifactsSchema.parse(payload);
}

export async function fetchStoryStyles() {
  const payload = await fetchJson("/v1/styles/story");
  return styleItemsSchema.parse(payload);
}

export async function fetchImageStyles() {
  const payload = await fetchJson("/v1/styles/image");
  return styleItemsSchema.parse(payload);
}

export async function generateRenderSpec(sceneId: string, styleId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/render-spec`, {
    method: "POST",
    body: JSON.stringify({ style_id: styleId })
  });
  return artifactIdSchema.parse(payload);
}

export async function generateRender(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/render`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}

export async function fetchScenes(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/scenes`);
  return scenesSchema.parse(payload);
}

export async function autoChunkScenes(params: {
  storyId: string;
  sourceText: string;
  maxScenes?: number;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/scenes/auto-chunk`, {
    method: "POST",
    body: JSON.stringify({
      source_text: params.sourceText,
      max_scenes: params.maxScenes ?? 6
    })
  });
  return scenesSchema.parse(payload);
}

export async function generateSceneIntent(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/scene-intent`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}

export async function generatePanelPlan(sceneId: string, panelCount = 3) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/panel-plan`, {
    method: "POST",
    body: JSON.stringify({ panel_count: panelCount })
  });
  return artifactIdSchema.parse(payload);
}

export async function normalizePanelPlan(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/panel-plan/normalize`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}

export async function generateLayout(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/layout`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}

export async function generatePanelSemantics(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/generate/panel-semantics`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}

export async function evaluateQc(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/evaluate/qc`, {
    method: "POST"
  });
  return artifactIdSchema.parse(payload);
}
