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
  styleItemsSchema,
  charactersSchema,
  storyGenerateResponseSchema,
  storyProgressSchema,
  jobStatusSchema,
  sceneGenerateFullSchema,
  characterRefsSchema,
  characterRefSchema,
  characterGenerateRefsResponseSchema,
  dialogueSuggestionsSchema,
  dialogueLayerSchema,
  episodesSchema,
  episodeSchema,
  exportSchema,
  characterVariantsSchema,
  characterVariantSchema,
  characterVariantSuggestionsSchema,
  characterVariantGenerationResultsSchema,
  sceneEstimationResponseSchema,
  libraryCharactersSchema,
  // Actor/Casting System
  actorCharacterReadSchema,
  actorCharactersReadSchema,
  actorVariantReadSchema,
  generateActorResponseSchema,
  deleteActorResponseSchema,
  deleteVariantResponseSchema,
  type CharacterTraitsInput
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

export async function setStoryStyleDefaults(params: {
  storyId: string;
  defaultStoryStyle: string;
  defaultImageStyle: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/set-style-defaults`, {
    method: "POST",
    body: JSON.stringify({
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

export async function fetchStoryProgress(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/progress`);
  return storyProgressSchema.parse(payload);
}

export async function fetchStories(projectId: string) {
  const payload = await fetchJson(`/v1/projects/${projectId}/stories`);
  return storiesSchema.parse(payload);
}

export async function fetchCharacters(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/characters`);
  return charactersSchema.parse(payload);
}

export async function createCharacter(params: {
  storyId: string;
  name: string;
  description?: string | null;
  role?: string;
  identityLine?: string | null;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/characters`, {
    method: "POST",
    body: JSON.stringify({
      name: params.name,
      description: params.description ?? null,
      role: params.role ?? "secondary",
      identity_line: params.identityLine ?? null
    })
  });
  return charactersSchema.element.parse(payload);
}

export async function updateCharacter(params: {
  characterId: string;
  name?: string | null;
  description?: string | null;
  role?: string | null;
  identityLine?: string | null;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}`, {
    method: "PATCH",
    body: JSON.stringify({
      name: params.name ?? undefined,
      description: params.description ?? undefined,
      role: params.role ?? undefined,
      identity_line: params.identityLine ?? undefined
    })
  });
  return charactersSchema.element.parse(payload);
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

export async function generateSceneFull(params: {
  sceneId: string;
  panelCount?: number;
  styleId: string;
  genre?: string | null;
  promptOverride?: string | null;
}) {
  const payload = await fetchJson(`/v1/scenes/${params.sceneId}/generate/full`, {
    method: "POST",
    body: JSON.stringify({
      panel_count: params.panelCount ?? 4,
      style_id: params.styleId,
      genre: params.genre ?? null,
      prompt_override: params.promptOverride ?? null
    })
  });
  return sceneGenerateFullSchema.parse(payload);
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



export async function estimateSceneCount(params: {
  storyId?: string;
  sourceText?: string;
  useLlm?: boolean;
}) {
  const url = params.storyId 
    ? `/v1/stories/${params.storyId}/estimate-scenes`
    : "/v1/utils/estimate-scenes";
    
  const payload = await fetchJson(url, {
    method: "POST",
    body: JSON.stringify({
      source_text: params.sourceText ?? null,
      use_llm: params.useLlm ?? true
    })
  });
  return sceneEstimationResponseSchema.parse(payload);
}


export async function generateStoryBlueprint(params: {
  storyId: string;
  sourceText: string;
  maxScenes?: number;
  panelCount?: number;
  styleId?: string;
  maxCharacters?: number;
  generateRenderSpec?: boolean;
  allowAppend?: boolean;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/generate/blueprint`, {
    method: "POST",
    body: JSON.stringify({
      source_text: params.sourceText,
      max_scenes: params.maxScenes ?? 6,
      panel_count: params.panelCount ?? 3,
      style_id: params.styleId ?? null,
      max_characters: params.maxCharacters ?? 6,
      generate_render_spec: params.generateRenderSpec ?? true,
      allow_append: params.allowAppend ?? false
    })
  });
  return storyGenerateResponseSchema.parse(payload);
}

export async function generateStoryBlueprintAsync(params: {
  storyId: string;
  sourceText: string;
  maxScenes?: number;
  panelCount?: number;
  styleId?: string;
  maxCharacters?: number;
  generateRenderSpec?: boolean;
  allowAppend?: boolean;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/generate/blueprint_async`, {
    method: "POST",
    body: JSON.stringify({
      source_text: params.sourceText,
      max_scenes: params.maxScenes ?? 6,
      panel_count: params.panelCount ?? 3,
      style_id: params.styleId ?? null,
      max_characters: params.maxCharacters ?? 6,
      generate_render_spec: params.generateRenderSpec ?? true,
      allow_append: params.allowAppend ?? false
    })
  });
  return jobStatusSchema.parse(payload);
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

// Character Reference Image APIs

export async function fetchCharacterRefs(characterId: string) {
  const payload = await fetchJson(`/v1/characters/${characterId}/refs`);
  return characterRefsSchema.parse(payload);
}

export async function fetchCharacterVariants(params: { storyId: string; characterId: string }) {
  const payload = await fetchJson(
    `/v1/stories/${params.storyId}/characters/${params.characterId}/variants`
  );
  return characterVariantsSchema.parse(payload);
}

export async function fetchCharacterVariantSuggestions(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/character-variant-suggestions`);
  return characterVariantSuggestionsSchema.parse(payload);
}

export async function refreshCharacterVariantSuggestions(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/character-variant-suggestions/refresh`, {
    method: "POST"
  });
  return characterVariantSuggestionsSchema.parse(payload);
}

export async function generateCharacterVariantSuggestions(params: {
  storyId: string;
  characterId?: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/character-variant-suggestions/generate`, {
    method: "POST",
    body: JSON.stringify({ character_id: params.characterId ?? null })
  });
  return characterVariantGenerationResultsSchema.parse(payload);
}

export async function createCharacterVariant(params: {
  storyId: string;
  characterId: string;
  variantType: string;
  overrideAttributes?: Record<string, unknown>;
  referenceImageId?: string | null;
  isActiveForStory?: boolean;
}) {
  const payload = await fetchJson(
    `/v1/stories/${params.storyId}/characters/${params.characterId}/variants`,
    {
      method: "POST",
      body: JSON.stringify({
        variant_type: params.variantType,
        override_attributes: params.overrideAttributes ?? {},
        reference_image_id: params.referenceImageId ?? null,
        is_active_for_story: params.isActiveForStory ?? true
      })
    }
  );
  return characterVariantSchema.parse(payload);
}

export async function activateCharacterVariant(params: {
  storyId: string;
  characterId: string;
  variantId: string;
  isActiveForStory?: boolean;
}) {
  const payload = await fetchJson(
    `/v1/stories/${params.storyId}/characters/${params.characterId}/variants/${params.variantId}/activate`,
    {
      method: "POST",
      body: JSON.stringify({
        is_active_for_story: params.isActiveForStory ?? true
      })
    }
  );
  return characterVariantSchema.parse(payload);
}

export async function generateCharacterRefs(params: {
  characterId: string;
  refTypes?: string[];
  countPerType?: number;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}/generate-refs`, {
    method: "POST",
    body: JSON.stringify({
      ref_types: params.refTypes ?? ["face"],
      count_per_type: params.countPerType ?? 2
    })
  });
  return characterGenerateRefsResponseSchema.parse(payload);
}

export async function approveCharacterRef(params: {
  characterId: string;
  referenceImageId: string;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}/approve-ref`, {
    method: "POST",
    body: JSON.stringify({
      reference_image_id: params.referenceImageId
    })
  });
  return characterRefSchema.parse(payload);
}

export async function deleteCharacterRef(params: {
  characterId: string;
  referenceImageId: string;
}) {
  await fetchJson(`/v1/characters/${params.characterId}/refs/${params.referenceImageId}`, {
    method: "DELETE"
  });
  return null;
}

export async function setPrimaryCharacterRef(params: {
  characterId: string;
  referenceImageId: string;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}/set-primary-ref`, {
    method: "POST",
    body: JSON.stringify({
      reference_image_id: params.referenceImageId
    })
  });
  return characterRefSchema.parse(payload);
}

export async function approveCharacter(characterId: string) {
  const payload = await fetchJson(`/v1/characters/${characterId}/approve`, {
    method: "POST"
  });
  return charactersSchema.element.parse(payload);
}

// Dialogue APIs

export async function fetchDialogueSuggestions(sceneId: string) {
  const payload = await fetchJson(`/v1/scenes/${sceneId}/dialogue/suggestions`);
  return dialogueSuggestionsSchema.parse(payload);
}

export async function fetchEpisodes(storyId: string) {
  const payload = await fetchJson(`/v1/stories/${storyId}/episodes`);
  return episodesSchema.parse(payload);
}

export async function createEpisode(params: {
  storyId: string;
  title: string;
  defaultStoryStyle: string;
  defaultImageStyle: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/episodes`, {
    method: "POST",
    body: JSON.stringify({
      title: params.title,
      default_story_style: params.defaultStoryStyle,
      default_image_style: params.defaultImageStyle
    })
  });
  return episodeSchema.parse(payload);
}

export async function setEpisodeScenes(params: { episodeId: string; sceneIds: string[] }) {
  const payload = await fetchJson(`/v1/episodes/${params.episodeId}/scenes`, {
    method: "POST",
    body: JSON.stringify({ scene_ids_ordered: params.sceneIds })
  });
  return payload;
}

export async function createEpisodeExport(episodeId: string) {
  const payload = await fetchJson(`/v1/episodes/${episodeId}/export`, {
    method: "POST"
  });
  return exportSchema.parse(payload);
}

export async function finalizeExport(exportId: string) {
  const payload = await fetchJson(`/v1/exports/${exportId}/finalize`, {
    method: "POST"
  });
  return exportSchema.parse(payload);
}

export async function generateVideoExport(exportId: string) {
  const payload = await fetchJson(`/v1/exports/${exportId}/generate-video`, {
    method: "POST"
  });
  return exportSchema.parse(payload);
}

export async function fetchExport(exportId: string) {
  const payload = await fetchJson(`/v1/exports/${exportId}`);
  return exportSchema.parse(payload);
}

export async function fetchDialogueLayer(sceneId: string) {
  try {
    const payload = await fetchJson(`/v1/scenes/${sceneId}/dialogue`);
    return dialogueLayerSchema.parse(payload);
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      const status = (error as { status?: number }).status;
      if (status === 404) return null;
    }
    throw error;
  }
}

export async function createDialogueLayer(params: {
  sceneId: string;
  bubbles: Array<{
    bubble_id: string;
    panel_id: number;
    text: string;
    position: { x: number; y: number };
    size: { w: number; h: number };
    tail?: { x: number; y: number } | null;
  }>;
}) {
  const payload = await fetchJson(`/v1/scenes/${params.sceneId}/dialogue`, {
    method: "POST",
    body: JSON.stringify({ bubbles: params.bubbles })
  });
  return payload;
}

export async function updateDialogueLayer(params: {
  dialogueId: string;
  bubbles: Array<{
    bubble_id: string;
    panel_id: number;
    text: string;
    position: { x: number; y: number };
    size: { w: number; h: number };
    tail?: { x: number; y: number } | null;
  }>;
}) {
  const payload = await fetchJson(`/v1/dialogue/${params.dialogueId}`, {
    method: "PUT",
    body: JSON.stringify({ bubbles: params.bubbles })
  });
  return payload;
}

// Character Library APIs

export async function saveToLibrary(params: {
  characterId: string;
  generationPrompt?: string;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}/save-to-library`, {
    method: "POST",
    body: JSON.stringify({
      generation_prompt: params.generationPrompt ?? null
    })
  });
  return payload;
}

export async function importReferenceFromLibrary(params: {
  characterId: string;
  libraryCharacterId: string;
}) {
  const payload = await fetchJson(`/v1/characters/${params.characterId}/import-from-library`, {
    method: "POST",
    body: JSON.stringify({
      library_character_id: params.libraryCharacterId
    })
  });
  return payload;
}

export async function removeFromLibrary(characterId: string) {
  const payload = await fetchJson(`/v1/characters/${characterId}/remove-from-library`, {
    method: "POST"
  });
  return payload;
}

export async function fetchLibraryCharacters(projectId: string) {
  const payload = await fetchJson(`/v1/projects/${projectId}/library/characters`);
  return libraryCharactersSchema.parse(payload);
}

export async function loadFromLibrary(params: {
  storyId: string;
  libraryCharacterId: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/characters/load-from-library`, {
    method: "POST",
    body: JSON.stringify({
      library_character_id: params.libraryCharacterId
    })
  });
  return payload;
}

export async function generateWithReference(params: {
  storyId: string;
  libraryCharacterId: string;
  variantDescription?: string;
  variantType?: string;
}) {
  const payload = await fetchJson(`/v1/stories/${params.storyId}/characters/generate-with-reference`, {
    method: "POST",
    body: JSON.stringify({
      library_character_id: params.libraryCharacterId,
      variant_description: params.variantDescription ?? null,
      variant_type: params.variantType ?? "story_context"
    })
  });
  return payload;
}

// ============================================================================
// Actor/Casting System APIs (Global Actors)
// ============================================================================

/**
 * Generate a new character profile sheet (preview before saving).
 * Uses global endpoint - actors are not tied to projects.
 */
export async function generateActor(params: {
  storyStyleId: string;
  imageStyleId: string;
  traits: CharacterTraitsInput;
}) {
  const payload = await fetchJson(`/v1/casting/generate`, {
    method: "POST",
    body: JSON.stringify({
      story_style_id: params.storyStyleId,
      image_style_id: params.imageStyleId,
      traits: params.traits
    })
  });
  return generateActorResponseSchema.parse(payload);
}

/**
 * Save a generated character to the global actor library.
 */
export async function saveActor(params: {
  imageId: string;
  displayName: string;
  description?: string | null;
  traits: CharacterTraitsInput;
  storyStyleId: string;
  imageStyleId: string;
}) {
  const payload = await fetchJson(`/v1/casting/save`, {
    method: "POST",
    body: JSON.stringify({
      image_id: params.imageId,
      display_name: params.displayName,
      description: params.description ?? null,
      traits: params.traits,
      story_style_id: params.storyStyleId,
      image_style_id: params.imageStyleId
    })
  });
  return actorCharacterReadSchema.parse(payload);
}

/**
 * List all actors in the global library.
 * Optionally filter by project to include project-specific actors.
 */
export async function fetchActorLibrary(projectId?: string) {
  const url = projectId
    ? `/v1/casting/library?project_id=${projectId}`
    : `/v1/casting/library`;
  const payload = await fetchJson(url);
  return actorCharactersReadSchema.parse(payload);
}

/**
 * Get a character with all its global variants.
 */
export async function fetchActor(characterId: string) {
  const payload = await fetchJson(`/v1/casting/characters/${characterId}`);
  return actorCharacterReadSchema.parse(payload);
}

/**
 * List all global variants for a character.
 */
export async function fetchActorVariants(characterId: string) {
  const payload = await fetchJson(`/v1/casting/characters/${characterId}/variants`);
  return actorVariantReadSchema.array().parse(payload);
}

/**
 * Generate a new variant using an existing variant as reference.
 */
export async function generateActorVariant(params: {
  characterId: string;
  baseVariantId: string;
  traitChanges: CharacterTraitsInput;
  storyStyleId?: string | null;
  imageStyleId?: string | null;
  variantName?: string | null;
}) {
  const payload = await fetchJson(`/v1/casting/characters/${params.characterId}/variants/generate`, {
    method: "POST",
    body: JSON.stringify({
      base_variant_id: params.baseVariantId,
      trait_changes: params.traitChanges,
      story_style_id: params.storyStyleId ?? null,
      image_style_id: params.imageStyleId ?? null,
      variant_name: params.variantName ?? null
    })
  });
  return actorVariantReadSchema.parse(payload);
}

/**
 * Import a character from an image URL or local file path.
 * For local development, you can use file paths like "/path/to/image.png" or "~/images/char.png"
 */
export async function importActor(params: {
  imageUrl: string;  // URL or local file path
  displayName: string;
  description?: string | null;
  traits?: CharacterTraitsInput | null;
  storyStyleId?: string | null;
  imageStyleId?: string | null;
}) {
  const payload = await fetchJson(`/v1/casting/import`, {
    method: "POST",
    body: JSON.stringify({
      image_url: params.imageUrl,
      display_name: params.displayName,
      description: params.description ?? null,
      traits: params.traits ?? {},
      story_style_id: params.storyStyleId ?? null,
      image_style_id: params.imageStyleId ?? null
    })
  });
  return actorCharacterReadSchema.parse(payload);
}

/**
 * Delete a character variant (cannot delete default variant).
 */
export async function deleteActorVariant(variantId: string) {
  const payload = await fetchJson(`/v1/casting/variants/${variantId}`, {
    method: "DELETE"
  });
  return deleteVariantResponseSchema.parse(payload);
}

/**
 * Remove a character from the library (soft delete).
 */
export async function deleteActor(characterId: string) {
  const payload = await fetchJson(`/v1/casting/characters/${characterId}`, {
    method: "DELETE"
  });
  return deleteActorResponseSchema.parse(payload);
}
