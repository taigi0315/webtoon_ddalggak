import { z } from "zod";

export const healthSchema = z.object({
  status: z.string()
});

export const projectSchema = z.object({
  project_id: z.string().uuid(),
  name: z.string()
});

export const storySchema = z.object({
  story_id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string(),
  default_story_style: z.string(),
  default_image_style: z.string()
});

export const sceneSchema = z.object({
  scene_id: z.string().uuid(),
  story_id: z.string().uuid(),
  environment_id: z.string().uuid().nullable(),
  source_text: z.string(),
  planning_locked: z.boolean(),
  story_style_override: z.string().nullable(),
  image_style_override: z.string().nullable()
});

export const projectsSchema = z.array(projectSchema);
export const storiesSchema = z.array(storySchema);
export const scenesSchema = z.array(sceneSchema);

export const artifactIdSchema = z.object({
  artifact_id: z.string().uuid()
});

export const artifactSchema = z.object({
  artifact_id: z.string().uuid(),
  scene_id: z.string().uuid(),
  type: z.string(),
  version: z.number(),
  parent_id: z.string().uuid().nullable(),
  payload: z.record(z.any())
});

export const artifactsSchema = z.array(artifactSchema);

export const styleItemSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string()
});

export const styleItemsSchema = z.array(styleItemSchema);

export type HealthStatus = z.infer<typeof healthSchema>;
export type Project = z.infer<typeof projectSchema>;
export type Story = z.infer<typeof storySchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type ArtifactIdResponse = z.infer<typeof artifactIdSchema>;
export type Artifact = z.infer<typeof artifactSchema>;
export type StyleItem = z.infer<typeof styleItemSchema>;
