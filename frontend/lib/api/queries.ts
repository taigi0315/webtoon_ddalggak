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
  storySchema
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

export async function fetchScenes(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/scenes`);
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
