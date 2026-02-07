"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchActorLibrary,
  fetchActor,
  fetchActorVariants,
  generateActor,
  saveActor,
  generateActorVariant,
  importActor,
  deleteActor,
  deleteActorVariant,
  fetchImageStyles
} from "@/lib/api/queries";
import type {
  ActorCharacterRead,
  ActorVariantRead,
  CharacterTraitsInput,
  StyleItem
} from "@/lib/api/types";
import { getImageUrl } from "@/lib/utils/media";

type GenerationState = {
  imageUrl: string | null;
  imageId: string | null;
  traits: CharacterTraitsInput;
  isGenerating: boolean;
};

export default function CastingStudioPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [selectedActorId, setSelectedActorId] = useState("");
  const [activeTab, setActiveTab] = useState<"library" | "generate" | "import">("library");

  // Generation state
  const [generationState, setGenerationState] = useState<GenerationState>({
    imageUrl: null,
    imageId: null,
    traits: {},
    isGenerating: false
  });

  // Form state for generation
  const [imageStyleId, setImageStyleId] = useState("default");
  const [traits, setTraits] = useState<CharacterTraitsInput>({
    gender: null,
    age_range: null,
    face_traits: null,
    hair_traits: null,
    mood: null,
    custom_prompt: null
  });

  // Queries
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects
  });

  const imageStylesQuery = useQuery({
    queryKey: ["imageStyles"],
    queryFn: fetchImageStyles
  });

  const libraryQuery = useQuery({
    queryKey: ["actorLibrary", projectId],
    queryFn: () => fetchActorLibrary(projectId),
    enabled: projectId.length > 0
  });

  // Load from localStorage
  useEffect(() => {
    const storedProjectId = window.localStorage.getItem("lastProjectId") ?? "";
    if (storedProjectId) setProjectId(storedProjectId);
  }, []);

  useEffect(() => {
    if (projectId) window.localStorage.setItem("lastProjectId", projectId);
  }, [projectId]);

  // Mutations
  const generateMutation = useMutation({
    mutationFn: generateActor,
    onSuccess: (data) => {
      setGenerationState({
        imageUrl: data.image_url,
        imageId: data.image_id,
        traits: data.traits_used as CharacterTraitsInput,
        isGenerating: false
      });
    },
    onError: () => {
      setGenerationState((prev) => ({ ...prev, isGenerating: false }));
    }
  });

  const saveMutation = useMutation({
    mutationFn: saveActor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actorLibrary", projectId] });
      setGenerationState({ imageUrl: null, imageId: null, traits: {}, isGenerating: false });
      setActiveTab("library");
    }
  });

  const handleGenerate = () => {
    if (!projectId) return;
    setGenerationState((prev) => ({ ...prev, isGenerating: true }));
    generateMutation.mutate({
      imageStyleId,
      traits
    });
  };

  const selectedActor = libraryQuery.data?.find(
    (actor) => actor.character_id === selectedActorId
  );

  if (!projectId) {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink">Casting Studio</h1>
          <p className="mt-2 text-slate-500">
            Create and manage reusable characters (actors) for your stories.
          </p>

          <div className="mt-6">
            <label className="text-sm font-semibold text-ink">Select Project</label>
            <select
              className="input w-full mt-2"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              <option value="">Select project</option>
              {projectsQuery.data?.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-6">
            <Link href="/studio/story" className="btn-ghost text-sm">
              &larr; Back to Story Editor
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="max-w-6xl mx-auto">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Casting Studio</h1>
            <p className="mt-1 text-slate-500">
              Create reusable actors independent of story context.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              className="input text-sm"
              value={projectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                setSelectedActorId("");
              }}
            >
              {projectsQuery.data?.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-6 flex gap-2 border-b border-slate-200 pb-3">
          <button
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
              activeTab === "library"
                ? "bg-white text-indigo-600 border-b-2 border-indigo-500"
                : "text-slate-500 hover:text-slate-700"
            }`}
            onClick={() => setActiveTab("library")}
          >
            Actor Library
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
              activeTab === "generate"
                ? "bg-white text-indigo-600 border-b-2 border-indigo-500"
                : "text-slate-500 hover:text-slate-700"
            }`}
            onClick={() => setActiveTab("generate")}
          >
            Generate New Actor
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
              activeTab === "import"
                ? "bg-white text-indigo-600 border-b-2 border-indigo-500"
                : "text-slate-500 hover:text-slate-700"
            }`}
            onClick={() => setActiveTab("import")}
          >
            Import from Image
          </button>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === "library" && (
            <LibraryTab
              projectId={projectId}
              actors={libraryQuery.data ?? []}
              isLoading={libraryQuery.isLoading}
              selectedActorId={selectedActorId}
              onSelectActor={setSelectedActorId}
              selectedActor={selectedActor}
            />
          )}

          {activeTab === "generate" && (
            <GenerateTab
              projectId={projectId}
              imageStyles={imageStylesQuery.data ?? []}
              imageStyleId={imageStyleId}
              traits={traits}
              generationState={generationState}
              onImageStyleChange={setImageStyleId}
              onTraitsChange={setTraits}
              onGenerate={handleGenerate}
              onSave={(displayName, description) => {
                if (!generationState.imageId) return;
                saveMutation.mutate({
                  imageId: generationState.imageId,
                  displayName,
                  description,
                  traits: generationState.traits,
                  imageStyleId
                });
              }}
              isSaving={saveMutation.isPending}
            />
          )}

          {activeTab === "import" && (
            <ImportTab
              projectId={projectId}
              imageStyles={imageStylesQuery.data ?? []}
              onImported={() => {
                queryClient.invalidateQueries({ queryKey: ["actorLibrary", projectId] });
                setActiveTab("library");
              }}
            />
          )}
        </div>
      </div>
    </section>
  );
}

function LibraryTab({
  projectId,
  actors,
  isLoading,
  selectedActorId,
  onSelectActor,
  selectedActor
}: {
  projectId: string;
  actors: ActorCharacterRead[];
  isLoading: boolean;
  selectedActorId: string;
  onSelectActor: (id: string) => void;
  selectedActor?: ActorCharacterRead;
}) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: deleteActor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actorLibrary", projectId] });
      onSelectActor("");
    }
  });

  if (isLoading) {
    return <div className="text-center py-12 text-slate-500">Loading actor library...</div>;
  }

  if (actors.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">No actors in library yet.</p>
        <p className="mt-2 text-sm text-slate-400">
          Generate a new actor or import from an image to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[280px,1fr]">
      {/* Actor List */}
      <aside className="space-y-3">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Actors</p>
        {actors.map((actor) => {
          const defaultVariant = actor.variants.find((v) => v.is_default);
          const imageUrl = defaultVariant?.reference_image_url ?? defaultVariant?.generated_image_urls?.[0];

          return (
            <button
              key={actor.character_id}
              className={`w-full text-left rounded-xl border p-3 transition ${
                actor.character_id === selectedActorId
                  ? "border-indigo-400 bg-indigo-50"
                  : "border-slate-200 bg-white/70 hover:border-indigo-200"
              }`}
              onClick={() => onSelectActor(actor.character_id)}
            >
              <div className="flex items-start gap-3">
                <div className="w-16 h-16 rounded-lg bg-slate-100 overflow-hidden flex-shrink-0">
                  {imageUrl ? (
                    <img
                      src={getImageUrl(imageUrl)}
                      alt={actor.display_name ?? actor.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-300">
                      ?
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-ink truncate">
                    {actor.display_name ?? actor.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {actor.variants.length} variant{actor.variants.length !== 1 ? "s" : ""}
                  </p>
                  {actor.gender && (
                    <p className="text-[10px] text-slate-400 capitalize mt-1">{actor.gender}</p>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </aside>

      {/* Actor Detail */}
      <div>
        {!selectedActor ? (
          <div className="card text-sm text-slate-500 text-center py-12">
            Select an actor from the list to view details.
          </div>
        ) : (
          <ActorDetail
            actor={selectedActor}
            onDelete={() => deleteMutation.mutate(selectedActor.character_id)}
            isDeleting={deleteMutation.isPending}
          />
        )}
      </div>
    </div>
  );
}

function ActorDetail({
  actor,
  onDelete,
  isDeleting
}: {
  actor: ActorCharacterRead;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const queryClient = useQueryClient();
  const [showVariantForm, setShowVariantForm] = useState(false);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [previewVariantId, setPreviewVariantId] = useState<string | null>(null);

  const variantsQuery = useQuery({
    queryKey: ["actorVariants", actor.character_id],
    queryFn: () => fetchActorVariants(actor.character_id)
  });

  const deleteVariantMutation = useMutation({
    mutationFn: deleteActorVariant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actorVariants", actor.character_id] });
      queryClient.invalidateQueries({ queryKey: ["actorLibrary"] });
    }
  });

  const defaultVariant = actor.variants.find((v) => v.is_default);
  const previewVariant = previewVariantId
    ? actor.variants.find((v) => v.variant_id === previewVariantId)
    : defaultVariant;

  const imageUrl =
    previewVariant?.reference_image_url ?? previewVariant?.generated_image_urls?.[0];

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,320px]">
      {/* Main View */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-ink">
              {actor.display_name ?? actor.name}
            </h3>
            {actor.description && (
              <p className="text-xs text-slate-500 mt-1">{actor.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn-ghost text-xs text-rose-600"
              onClick={onDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "Removing..." : "Remove from Library"}
            </button>
          </div>
        </div>

        {/* Preview Image */}
        <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft">
          {imageUrl ? (
            <div className="relative h-[480px] w-full overflow-auto rounded-xl bg-slate-100">
              <img
                src={getImageUrl(imageUrl)}
                alt={actor.display_name ?? actor.name}
                className="mx-auto rounded-xl object-contain max-h-full"
              />
            </div>
          ) : (
            <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              No image available.
            </div>
          )}
        </div>

        {/* Variant Thumbnails */}
        {actor.variants.length > 0 && (
          <div className="mt-6">
            <p className="text-xs text-slate-500 mb-3">
              Click a variant to preview. The default variant is used as identity anchor.
            </p>
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
              {actor.variants.map((variant) => {
                const vUrl = variant.reference_image_url ?? variant.generated_image_urls?.[0];
                return (
                  <div key={variant.variant_id} className="relative group">
                    <button
                      className={`w-full aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                        previewVariantId === variant.variant_id ||
                        (!previewVariantId && variant.is_default)
                          ? "border-indigo-500 ring-2 ring-indigo-300"
                          : "border-slate-200 hover:border-indigo-400"
                      }`}
                      onClick={() => setPreviewVariantId(variant.variant_id)}
                    >
                      {vUrl ? (
                        <img
                          src={getImageUrl(vUrl)}
                          alt={variant.variant_name ?? "Variant"}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full bg-slate-100 flex items-center justify-center text-slate-300">
                          ?
                        </div>
                      )}
                    </button>

                    {!variant.is_default && (
                      <button
                        className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-red-500 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteVariantMutation.mutate(variant.variant_id);
                        }}
                        disabled={deleteVariantMutation.isPending}
                        title="Delete this variant"
                      >
                        &times;
                      </button>
                    )}

                    {variant.is_default && (
                      <div className="absolute bottom-1 left-1 right-1 bg-indigo-500 text-white text-[10px] text-center rounded py-0.5">
                        Default
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <aside className="card">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold text-slate-500">Gender</p>
            <p className="text-sm text-ink capitalize">{actor.gender ?? "Not specified"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500">Age Range</p>
            <p className="text-sm text-ink">{actor.age_range ?? "Not specified"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500">Default Style</p>
            <p className="text-sm text-ink">
              {actor.default_image_style_id ?? "default"}
            </p>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <h4 className="text-sm font-semibold text-ink">Create Variant</h4>
          <p className="mt-1 text-xs text-slate-500">
            Generate a new look while preserving identity.
          </p>

          <button
            className="btn-secondary w-full text-xs mt-3"
            onClick={() => setShowVariantForm(!showVariantForm)}
          >
            {showVariantForm ? "Cancel" : "+ New Variant"}
          </button>

          {showVariantForm && defaultVariant && (
            <VariantForm
              actor={actor}
              baseVariant={defaultVariant}
              onCreated={() => {
                queryClient.invalidateQueries({ queryKey: ["actorVariants", actor.character_id] });
                queryClient.invalidateQueries({ queryKey: ["actorLibrary"] });
                setShowVariantForm(false);
              }}
            />
          )}
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <h4 className="text-sm font-semibold text-ink">Variants ({actor.variants.length})</h4>
          <div className="mt-3 space-y-2 max-h-[300px] overflow-y-auto">
            {actor.variants.map((variant) => (
              <div
                key={variant.variant_id}
                className={`rounded-lg border px-3 py-2 text-xs ${
                  variant.is_default
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">
                    {variant.variant_name ?? variant.variant_type}
                  </span>
                  {variant.is_default && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                      Default
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">{variant.variant_type}</p>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

function VariantForm({
  actor,
  baseVariant,
  onCreated
}: {
  actor: ActorCharacterRead;
  baseVariant: ActorVariantRead;
  onCreated: () => void;
}) {
  const [variantName, setVariantName] = useState("");
  const [hairChanges, setHairChanges] = useState("");
  const [moodChanges, setMoodChanges] = useState("");
  const [customChanges, setCustomChanges] = useState("");

  const generateMutation = useMutation({
    mutationFn: generateActorVariant,
    onSuccess: () => {
      onCreated();
    }
  });

  const handleGenerate = () => {
    const traitChanges: CharacterTraitsInput = {};
    if (hairChanges) traitChanges.hair_traits = hairChanges;
    if (moodChanges) traitChanges.mood = moodChanges;
    if (customChanges) traitChanges.custom_prompt = customChanges;

    generateMutation.mutate({
      characterId: actor.character_id,
      baseVariantId: baseVariant.variant_id,
      traitChanges,
      variantName: variantName || null
    });
  };

  return (
    <div className="mt-4 space-y-3">
      <div>
        <label className="text-xs font-semibold text-slate-500">Variant Name</label>
        <input
          className="input mt-1 w-full text-sm"
          placeholder="e.g., Summer Outfit"
          value={variantName}
          onChange={(e) => setVariantName(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500">Hair Changes</label>
        <input
          className="input mt-1 w-full text-sm"
          placeholder="e.g., Shorter hair, dyed pink"
          value={hairChanges}
          onChange={(e) => setHairChanges(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500">Mood / Expression</label>
        <input
          className="input mt-1 w-full text-sm"
          placeholder="e.g., Angry, determined"
          value={moodChanges}
          onChange={(e) => setMoodChanges(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-slate-500">Other Changes</label>
        <textarea
          className="textarea mt-1 w-full text-sm min-h-[60px]"
          placeholder="e.g., Wearing a red dress, holding a sword"
          value={customChanges}
          onChange={(e) => setCustomChanges(e.target.value)}
        />
      </div>
      <button
        className="btn-primary w-full text-xs"
        onClick={handleGenerate}
        disabled={generateMutation.isPending || (!hairChanges && !moodChanges && !customChanges)}
      >
        {generateMutation.isPending ? "Generating..." : "Generate Variant"}
      </button>
      {generateMutation.isError && (
        <p className="text-xs text-rose-500">
          {generateMutation.error instanceof Error
            ? generateMutation.error.message
            : "Failed to generate variant."}
        </p>
      )}
    </div>
  );
}

function GenerateTab({
  projectId,
  imageStyles,
  imageStyleId,
  traits,
  generationState,
  onImageStyleChange,
  onTraitsChange,
  onGenerate,
  onSave,
  isSaving
}: {
  projectId: string;
  imageStyles: StyleItem[];
  imageStyleId: string;
  traits: CharacterTraitsInput;
  generationState: GenerationState;
  onImageStyleChange: (id: string) => void;
  onTraitsChange: (traits: CharacterTraitsInput) => void;
  onGenerate: () => void;
  onSave: (displayName: string, description: string | null) => void;
  isSaving: boolean;
}) {
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,360px]">
      {/* Preview */}
      <div className="card">
        <h3 className="text-lg font-semibold text-ink">Preview</h3>
        <p className="text-xs text-slate-500 mt-1">
          Generated profile sheet will appear here. Review before saving.
        </p>

        <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft">
          {generationState.imageUrl ? (
            <div className="relative h-[520px] w-full overflow-auto rounded-xl bg-slate-100">
              <img
                src={getImageUrl(generationState.imageUrl)}
                alt="Generated character"
                className="mx-auto rounded-xl object-contain max-h-full"
              />
            </div>
          ) : generationState.isGenerating ? (
            <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              <div className="text-center">
                <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto"></div>
                <p className="mt-4">Generating profile sheet...</p>
              </div>
            </div>
          ) : (
            <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              Configure traits and click Generate to create a profile sheet.
            </div>
          )}
        </div>

        {/* Save Form (shown after generation) */}
        {generationState.imageId && (
          <div className="mt-6 p-4 rounded-xl border border-green-200 bg-green-50">
            <h4 className="text-sm font-semibold text-green-800">Save to Library</h4>
            <div className="mt-3 space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-500">Display Name *</label>
                <input
                  className="input mt-1 w-full"
                  placeholder="e.g., Hero Character"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500">Description</label>
                <textarea
                  className="textarea mt-1 w-full min-h-[80px]"
                  placeholder="Optional description..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="flex gap-3">
                <button
                  className="btn-primary flex-1"
                  onClick={() => onSave(displayName, description || null)}
                  disabled={isSaving || !displayName.trim()}
                >
                  {isSaving ? "Saving..." : "Save to Library"}
                </button>
                <button className="btn-ghost" onClick={onGenerate}>
                  Regenerate
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Form */}
      <aside className="card">
        <h3 className="text-sm font-semibold text-ink">Character Traits</h3>

        <div className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500">Image Style</label>
            <select
              className="input mt-1 w-full text-sm"
              value={imageStyleId}
              onChange={(e) => onImageStyleChange(e.target.value)}
            >
              <option value="default">Default</option>
              {imageStyles.map((style) => (
                <option key={style.id} value={style.id}>
                  {style.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Gender</label>
            <select
              className="input mt-1 w-full text-sm"
              value={traits.gender ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, gender: e.target.value || null })}
            >
              <option value="">Not specified</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="non-binary">Non-binary</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Age Range</label>
            <select
              className="input mt-1 w-full text-sm"
              value={traits.age_range ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, age_range: e.target.value || null })}
            >
              <option value="">Not specified</option>
              <option value="child">Child (5-12)</option>
              <option value="teen">Teen (13-19)</option>
              <option value="young_adult">Young Adult (20-35)</option>
              <option value="adult">Adult (36-55)</option>
              <option value="elderly">Elderly (56+)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Face Traits</label>
            <input
              className="input mt-1 w-full text-sm"
              placeholder="e.g., Sharp jawline, blue eyes"
              value={traits.face_traits ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, face_traits: e.target.value || null })}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Hair Traits</label>
            <input
              className="input mt-1 w-full text-sm"
              placeholder="e.g., Long black hair, wavy"
              value={traits.hair_traits ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, hair_traits: e.target.value || null })}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Mood / Expression</label>
            <input
              className="input mt-1 w-full text-sm"
              placeholder="e.g., Confident, mysterious"
              value={traits.mood ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, mood: e.target.value || null })}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Custom Description</label>
            <textarea
              className="textarea mt-1 w-full text-sm min-h-[80px]"
              placeholder="Additional details about the character..."
              value={traits.custom_prompt ?? ""}
              onChange={(e) => onTraitsChange({ ...traits, custom_prompt: e.target.value || null })}
            />
          </div>

          <button
            className="btn-primary w-full"
            onClick={onGenerate}
            disabled={generationState.isGenerating}
          >
            {generationState.isGenerating ? "Generating..." : "Generate Profile Sheet"}
          </button>
        </div>
      </aside>
    </div>
  );
}

function ImportTab({
  projectId,
  imageStyles,
  onImported
}: {
  projectId: string;
  imageStyles: StyleItem[];
  onImported: () => void;
}) {
  const [imageUrl, setImageUrl] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [imageStyleId, setImageStyleId] = useState("default");
  const [gender, setGender] = useState("");
  const [ageRange, setAgeRange] = useState("");

  const importMutation = useMutation({
    mutationFn: importActor,
    onSuccess: () => {
      onImported();
      setImageUrl("");
      setDisplayName("");
      setDescription("");
    }
  });

  const handleImport = () => {
    const traits: CharacterTraitsInput = {};
    if (gender) traits.gender = gender;
    if (ageRange) traits.age_range = ageRange;

    importMutation.mutate({
      imageUrl,
      displayName,
      description: description || null,
      traits,
      imageStyleId: imageStyleId !== "default" ? imageStyleId : null
    });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,360px]">
      {/* Preview */}
      <div className="card">
        <h3 className="text-lg font-semibold text-ink">Image Preview</h3>
        <p className="text-xs text-slate-500 mt-1">
          Paste an image URL to preview before importing.
        </p>

        <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft">
          {imageUrl ? (
            <div className="relative h-[480px] w-full overflow-auto rounded-xl bg-slate-100">
              <img
                src={getImageUrl(imageUrl)}
                alt="Import preview"
                className="mx-auto rounded-xl object-contain max-h-full"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = "";
                  (e.target as HTMLImageElement).alt = "Failed to load image";
                }}
              />
            </div>
          ) : (
            <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              Enter an image URL to preview.
            </div>
          )}
        </div>
      </div>

      {/* Form */}
      <aside className="card">
        <h3 className="text-sm font-semibold text-ink">Import Details</h3>

        <div className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500">Image URL *</label>
            <input
              className="input mt-1 w-full text-sm"
              placeholder="https://example.com/image.png"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Display Name *</label>
            <input
              className="input mt-1 w-full text-sm"
              placeholder="e.g., Imported Hero"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Description</label>
            <textarea
              className="textarea mt-1 w-full text-sm min-h-[60px]"
              placeholder="Optional description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Image Style</label>
            <select
              className="input mt-1 w-full text-sm"
              value={imageStyleId}
              onChange={(e) => setImageStyleId(e.target.value)}
            >
              <option value="default">Default</option>
              {imageStyles.map((style) => (
                <option key={style.id} value={style.id}>
                  {style.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Gender</label>
            <select
              className="input mt-1 w-full text-sm"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
            >
              <option value="">Not specified</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="non-binary">Non-binary</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500">Age Range</label>
            <select
              className="input mt-1 w-full text-sm"
              value={ageRange}
              onChange={(e) => setAgeRange(e.target.value)}
            >
              <option value="">Not specified</option>
              <option value="child">Child</option>
              <option value="teen">Teen</option>
              <option value="young_adult">Young Adult</option>
              <option value="adult">Adult</option>
              <option value="elderly">Elderly</option>
            </select>
          </div>

          <button
            className="btn-primary w-full"
            onClick={handleImport}
            disabled={importMutation.isPending || !imageUrl.trim() || !displayName.trim()}
          >
            {importMutation.isPending ? "Importing..." : "Import to Library"}
          </button>

          {importMutation.isError && (
            <p className="text-xs text-rose-500">
              {importMutation.error instanceof Error
                ? importMutation.error.message
                : "Failed to import character."}
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
