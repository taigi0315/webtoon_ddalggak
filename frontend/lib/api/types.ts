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
  default_image_style: z.string(),
  generation_status: z.string().nullable().optional(),
  generation_error: z.string().nullable().optional()
});

export const sceneSchema = z.object({
  scene_id: z.string().uuid(),
  story_id: z.string().uuid(),
  environment_id: z.string().uuid().nullable(),
  source_text: z.string(),
  scene_importance: z.string().nullable(),
  planning_locked: z.boolean(),
  story_style_override: z.string().nullable(),
  image_style_override: z.string().nullable()
});

export const projectsSchema = z.array(projectSchema);
export const storiesSchema = z.array(storySchema);
export const scenesSchema = z.array(sceneSchema);

export const characterSchema = z.object({
  character_id: z.string().uuid(),
  project_id: z.string().uuid(),
  canonical_code: z.string().nullable(),
  name: z.string(),
  description: z.string().nullable(),
  role: z.string(),
  gender: z.string().nullable(),
  age_range: z.string().nullable(),
  appearance: z.record(z.any()).nullable(),
  hair_description: z.string().nullable(),
  base_outfit: z.string().nullable(),
  identity_line: z.string().nullable(),
  approved: z.boolean()
});

export const charactersSchema = z.array(characterSchema);

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
  description: z.string(),
  image_url: z.string().nullable().optional()
});

export const styleItemsSchema = z.array(styleItemSchema);

export const storyGenerateResponseSchema = z.object({
  scenes: scenesSchema,
  characters: charactersSchema
});

export const storyProgressSchema = z.object({
  story_id: z.string().uuid(),
  status: z.string(),
  progress: z.record(z.any()).nullable().optional(),
  error: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional()
});

export const sceneGenerateFullSchema = z.object({
  scene_intent_artifact_id: z.string().uuid(),
  panel_plan_artifact_id: z.string().uuid(),
  panel_plan_normalized_artifact_id: z.string().uuid(),
  layout_template_artifact_id: z.string().uuid(),
  panel_semantics_artifact_id: z.string().uuid(),
  qc_report_artifact_id: z.string().uuid(),
  render_spec_artifact_id: z.string().uuid(),
  render_result_artifact_id: z.string().uuid(),
  blind_test_report_artifact_id: z.string().uuid()
});

export const characterRefSchema = z.object({
  reference_image_id: z.string().uuid(),
  character_id: z.string().uuid(),
  image_url: z.string(),
  ref_type: z.string(),
  approved: z.boolean(),
  is_primary: z.boolean(),
  metadata_: z.record(z.any())
});

export const characterRefsSchema = z.array(characterRefSchema);

export const characterVariantSchema = z.object({
  variant_id: z.string().uuid(),
  character_id: z.string().uuid(),
  story_id: z.string().uuid(),
  variant_type: z.string(),
  override_attributes: z.record(z.any()),
  reference_image_id: z.string().uuid().nullable(),
  is_active_for_story: z.boolean(),
  created_at: z.string().nullable().optional()
});

export const characterVariantsSchema = z.array(characterVariantSchema);

export const characterGenerateRefsResponseSchema = z.object({
  character_id: z.string().uuid(),
  generated_refs: characterRefsSchema
});

export const dialogueLineSchema = z.object({
  speaker: z.string(),
  type: z.string(),
  text: z.string()
});

export const dialoguePanelSchema = z.object({
  panel_id: z.number(),
  lines: z.array(dialogueLineSchema),
  notes: z.string().nullable().optional()
});

export const dialogueSuggestionsSchema = z.object({
  scene_id: z.string().uuid(),
  dialogue_by_panel: z.array(dialoguePanelSchema)
});

export type HealthStatus = z.infer<typeof healthSchema>;
export type Project = z.infer<typeof projectSchema>;
export type Story = z.infer<typeof storySchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type Character = z.infer<typeof characterSchema>;
export type ArtifactIdResponse = z.infer<typeof artifactIdSchema>;
export type Artifact = z.infer<typeof artifactSchema>;
export type StyleItem = z.infer<typeof styleItemSchema>;
export type StoryGenerateResponse = z.infer<typeof storyGenerateResponseSchema>;
export type CharacterRef = z.infer<typeof characterRefSchema>;
export type CharacterVariant = z.infer<typeof characterVariantSchema>;
export type CharacterGenerateRefsResponse = z.infer<typeof characterGenerateRefsResponseSchema>;
export type DialogueLine = z.infer<typeof dialogueLineSchema>;
export type DialoguePanel = z.infer<typeof dialoguePanelSchema>;
export type DialogueSuggestions = z.infer<typeof dialogueSuggestionsSchema>;

export const characterVariantSuggestionSchema = z.object({
  suggestion_id: z.string().uuid(),
  story_id: z.string().uuid(),
  character_id: z.string().uuid(),
  variant_type: z.string(),
  override_attributes: z.record(z.any()),
  created_at: z.string().nullable().optional()
});

export const characterVariantSuggestionsSchema = z.array(characterVariantSuggestionSchema);

export type CharacterVariantSuggestion = z.infer<typeof characterVariantSuggestionSchema>;
