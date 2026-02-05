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
  generation_prompt: z.string().nullable().optional(),
  is_library_saved: z.boolean().optional().default(false),
  narrative_description: z.string().nullable().optional(),
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

export const jobStatusSchema = z.object({
  job_id: z.string().uuid(),
  job_type: z.string(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  progress: z.record(z.any()).nullable().optional(),
  result: z.record(z.any()).nullable().optional(),
  error: z.string().nullable().optional()
});

export const sceneWorkflowStatusSchema = z.object({
  scene_id: z.string().uuid(),
  planning_locked: z.boolean(),
  planning_complete: z.boolean(),
  render_complete: z.boolean(),
  latest_artifacts: z.record(z.string(), z.string().uuid().nullable())
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
export type SceneWorkflowStatus = z.infer<typeof sceneWorkflowStatusSchema>;

export type CharacterRef = z.infer<typeof characterRefSchema>;
export type CharacterVariant = z.infer<typeof characterVariantSchema>;
export type CharacterGenerateRefsResponse = z.infer<typeof characterGenerateRefsResponseSchema>;
export type DialogueLine = z.infer<typeof dialogueLineSchema>;
export type DialoguePanel = z.infer<typeof dialoguePanelSchema>;
export type DialogueSuggestions = z.infer<typeof dialogueSuggestionsSchema>;

// Bubble type enum matching backend
export const BubbleTypeEnum = z.enum(["chat", "thought", "narration", "sfx"]);
export type BubbleType = z.infer<typeof BubbleTypeEnum>;

export const dialogueBubbleSchema = z.object({
  bubble_id: z.string(),
  panel_id: z.number(),
  bubble_type: BubbleTypeEnum.default("chat"),  // Enum: chat, thought, narration, sfx
  speaker: z.string().nullable().optional(),
  text: z.string(),
  position: z.object({ x: z.number(), y: z.number() }),
  size: z.object({ w: z.number(), h: z.number() }),
  tail: z.object({ x: z.number(), y: z.number() }).nullable().optional()
});

export const dialogueLayerSchema = z.object({
  dialogue_id: z.string().uuid(),
  scene_id: z.string().uuid(),
  bubbles: z.array(dialogueBubbleSchema),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional()
});

export type DialogueBubble = z.infer<typeof dialogueBubbleSchema>;
export type DialogueLayer = z.infer<typeof dialogueLayerSchema>;

export const episodeSchema = z.object({
  episode_id: z.string().uuid(),
  story_id: z.string().uuid(),
  title: z.string(),
  episode_number: z.number().nullable().optional(),
  default_image_style: z.string().nullable().optional(),
  scene_ids_ordered: z.array(z.string().uuid()).default([]),
  created_at: z.string().nullable().optional()
});

export const episodesSchema = z.array(episodeSchema);

export type Episode = z.infer<typeof episodeSchema>;

export const exportSchema = z.object({
  export_id: z.string().uuid(),
  episode_id: z.string().uuid().nullable().optional(),
  story_id: z.string().uuid().nullable().optional(),
  status: z.string().nullable().default(null),
  video_url: z.string().nullable().default(null),
  output_url: z.string().nullable().default(null),
  metadata_: z.record(z.any()).nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional()
});

export type Export = z.infer<typeof exportSchema>;

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

export const characterVariantGenerationResultSchema = z.object({
  character_id: z.string().uuid(),
  story_id: z.string().uuid(),
  variant_id: z.string().uuid().nullable().optional(),
  reference_image_id: z.string().uuid().nullable().optional(),
  variant_type: z.string().nullable().optional(),
  override_attributes: z.record(z.any()).nullable().optional(),
  status: z.string(),
  detail: z.string().nullable().optional()
});

export const characterVariantGenerationResultsSchema = z.array(
  characterVariantGenerationResultSchema
);

export type CharacterVariantGenerationResult = z.infer<
  typeof characterVariantGenerationResultSchema
>;


export const sceneAnalysisSchema = z.object({
  narrative_beats: z.number().nullable().optional(),
  estimated_duration_seconds: z.number().nullable().optional(),
  pacing: z.string().nullable().optional(),
  complexity: z.string().nullable().optional(),
  dialogue_density: z.string().nullable().optional(),
  key_moments: z.array(z.string()).nullable().optional()
});


export const sceneEstimationResponseSchema = z.object({
  recommended_count: z.number(),
  status: z.string(),
  message: z.string(),
  analysis: sceneAnalysisSchema.nullable().optional()
});

export type SceneAnalysis = z.infer<typeof sceneAnalysisSchema>;
export type SceneEstimationResponse = z.infer<typeof sceneEstimationResponseSchema>;

export const libraryCharacterSchema = z.object({
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
  generation_prompt: z.string().nullable(),
  approved: z.boolean(),
  primary_reference_image: characterRefSchema.nullable().optional()
});

export const saveToLibraryResponseSchema = z.object({
  character_id: z.string().uuid(),
  is_library_saved: z.boolean(),
  message: z.string()
});

export const loadFromLibraryResponseSchema = z.object({
  character_id: z.string().uuid(),
  story_id: z.string().uuid(),
  already_linked: z.boolean(),
  message: z.string()
});

export const generateWithReferenceResponseSchema = z.object({
  character_id: z.string().uuid(),
  story_id: z.string().uuid(),
  variant_id: z.string().uuid().nullable(),
  reference_image_id: z.string().uuid().nullable(),
  status: z.string(),
  message: z.string()
});

export const libraryCharactersSchema = z.array(libraryCharacterSchema);

export type LibraryCharacter = z.infer<typeof libraryCharacterSchema>;
export type SaveToLibraryResponse = z.infer<typeof saveToLibraryResponseSchema>;
export type LoadFromLibraryResponse = z.infer<typeof loadFromLibraryResponseSchema>;
export type GenerateWithReferenceResponse = z.infer<typeof generateWithReferenceResponseSchema>;

// ============================================================================
// Actor/Casting System Schemas
// ============================================================================

export const characterTraitsInputSchema = z.object({
  gender: z.string().nullable().optional(),
  age_range: z.string().nullable().optional(),
  face_traits: z.string().nullable().optional(),
  hair_traits: z.string().nullable().optional(),
  mood: z.string().nullable().optional(),
  custom_prompt: z.string().nullable().optional()
});

export const actorVariantReadSchema = z.object({
  variant_id: z.string().uuid(),
  character_id: z.string().uuid(),
  variant_name: z.string().nullable(),
  variant_type: z.string(),
  image_style_id: z.string().nullable(),
  traits: z.record(z.any()),
  is_default: z.boolean(),
  reference_image_url: z.string().nullable().optional(),
  generated_image_urls: z.array(z.string()).default([]),
  created_at: z.string().nullable().optional()
});

export const actorCharacterReadSchema = z.object({
  character_id: z.string().uuid(),
  project_id: z.string().uuid().nullable(),  // null for global actors
  display_name: z.string().nullable(),
  name: z.string(),
  description: z.string().nullable(),
  gender: z.string().nullable().optional(),
  age_range: z.string().nullable().optional(),
  default_image_style_id: z.string().nullable().optional(),
  is_library_saved: z.boolean().optional(),
  variants: z.array(actorVariantReadSchema).default([])
});

export const actorCharactersReadSchema = z.array(actorCharacterReadSchema);

export const generateActorResponseSchema = z.object({
  character_id: z.string().uuid().nullable(),
  image_url: z.string(),
  image_id: z.string().uuid(),
  traits_used: z.record(z.any()),
  status: z.string()
});

export const deleteActorResponseSchema = z.object({
  removed: z.boolean(),
  character_id: z.string()
});

export const deleteVariantResponseSchema = z.object({
  deleted: z.boolean()
});

export type CharacterTraitsInput = z.infer<typeof characterTraitsInputSchema>;
export type ActorVariantRead = z.infer<typeof actorVariantReadSchema>;
export type ActorCharacterRead = z.infer<typeof actorCharacterReadSchema>;
export type GenerateActorResponse = z.infer<typeof generateActorResponseSchema>;
export type DeleteActorResponse = z.infer<typeof deleteActorResponseSchema>;
export type DeleteVariantResponse = z.infer<typeof deleteVariantResponseSchema>;
