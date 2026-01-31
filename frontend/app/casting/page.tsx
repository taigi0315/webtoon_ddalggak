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
    importActorFromFile,
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

type GenerationState = {
    imageUrl: string | null;
    imageId: string | null;
    traits: CharacterTraitsInput;
    isGenerating: boolean;
};

export default function CastingStudioPage() {
    const queryClient = useQueryClient();
    const [projectId, setProjectId] = useState(""); // Optional project filter
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
        queryFn: () => fetchActorLibrary(projectId || undefined)
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
        setGenerationState((prev) => ({ ...prev, isGenerating: true }));
        generateMutation.mutate({
            imageStyleId,
            traits
        });
    };

    const selectedActor = libraryQuery.data?.find(
        (actor) => actor.character_id === selectedActorId
    );

    return (
        <section className="max-w-6xl mx-auto h-full">
            <div className="surface p-8 min-h-full">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-ink">Actor Library</h1>
                        <p className="mt-1 text-slate-500">
                            Create and manage reusable actors independent of stories.
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="text-xs font-semibold text-slate-500 mr-2">Filter by Project:</label>
                        <select
                            className="input text-sm w-48"
                            value={projectId}
                            onChange={(e) => {
                                setProjectId(e.target.value);
                                setSelectedActorId("");
                            }}
                        >
                            <option value="">All Global Actors</option>
                            {projectsQuery.data?.map((project) => (
                                <option key={project.project_id} value={project.project_id}>
                                    {project.name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Tabs */}
                <div className="mt-8 flex gap-2 border-b border-slate-200 pb-0">
                    <button
                        className={`px-6 py-3 text-sm font-medium rounded-t-lg transition border-t border-l border-r ${activeTab === "library"
                                ? "bg-white text-indigo-600 border-indigo-200 -mb-px border-b-white z-10"
                                : "bg-slate-50 text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-100"
                            }`}
                        onClick={() => setActiveTab("library")}
                    >
                        My Actors
                    </button>
                    <button
                        className={`px-6 py-3 text-sm font-medium rounded-t-lg transition border-t border-l border-r ${activeTab === "generate"
                                ? "bg-white text-indigo-600 border-indigo-200 -mb-px border-b-white z-10"
                                : "bg-slate-50 text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-100"
                            }`}
                        onClick={() => setActiveTab("generate")}
                    >
                        Generate New Actor
                    </button>
                    <button
                        className={`px-6 py-3 text-sm font-medium rounded-t-lg transition border-t border-l border-r ${activeTab === "import"
                                ? "bg-white text-indigo-600 border-indigo-200 -mb-px border-b-white z-10"
                                : "bg-slate-50 text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-100"
                            }`}
                        onClick={() => setActiveTab("import")}
                    >
                        Import form Image
                    </button>
                </div>

                {/* Tab Content */}
                <div className="py-6">
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

    const getImageUrl = (url: string) => {
        if (url.startsWith("/media/")) {
            return `http://localhost:8000${url}`;
        }
        return url;
    };

    if (isLoading) {
        return <div className="text-center py-12 text-slate-500">Loading actor library...</div>;
    }

    if (actors.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-slate-500">No actors in library.</p>
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
                <div className="max-h-[600px] overflow-y-auto space-y-3 pr-1">
                    {actors.map((actor) => {
                        const defaultVariant = actor.variants.find((v) => v.is_default);
                        const imageUrl = defaultVariant?.reference_image_url ?? defaultVariant?.generated_image_urls?.[0];

                        return (
                            <button
                                key={actor.character_id}
                                className={`w-full text-left rounded-xl border p-3 transition ${actor.character_id === selectedActorId
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
                </div>
            </aside>

            {/* Actor Detail */}
            <div>
                {!selectedActor ? (
                    <div className="card text-sm text-slate-500 text-center py-12 bg-slate-50/50">
                        Select an actor from the list to view details and manage variants.
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

    const deleteVariantMutation = useMutation({
        mutationFn: deleteActorVariant,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["actorLibrary"] });
        }
    });

    const defaultVariant = actor.variants.find((v) => v.is_default);
    const previewVariant = previewVariantId
        ? actor.variants.find((v) => v.variant_id === previewVariantId)
        : defaultVariant;

    const imageUrl =
        previewVariant?.reference_image_url ?? previewVariant?.generated_image_urls?.[0];

    const getImageUrl = (url: string) => {
        if (url.startsWith("/media/")) {
            return `http://localhost:8000${url}`;
        }
        return url;
    };

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
                            className="btn-ghost text-xs text-rose-600 hover:bg-rose-50"
                            onClick={onDelete}
                            disabled={isDeleting}
                        >
                            {isDeleting ? "Removing..." : "Remove from Library"}
                        </button>
                    </div>
                </div>

                {/* Preview Image */}
                <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft border border-slate-100">
                    {imageUrl ? (
                        <div className="relative h-[600px] w-full overflow-hidden rounded-xl bg-slate-100">
                            <img
                                src={getImageUrl(imageUrl)}
                                alt={actor.display_name ?? actor.name}
                                className="mx-auto h-full object-contain"
                            />
                            {/* Overlay Badge */}
                            {previewVariant?.is_default && (
                                <div className="absolute top-2 left-2 bg-indigo-600 text-white text-[10px] font-bold px-2 py-1 rounded shadow-sm">
                                    DEFAULT LOOK (Identity Anchor)
                                </div>
                            )}
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
                        <p className="text-xs text-slate-500 mb-3 uppercase tracking-wider font-semibold">
                            Variants
                        </p>
                        <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-8 gap-3">
                            {actor.variants.map((variant) => {
                                const vUrl = variant.reference_image_url ?? variant.generated_image_urls?.[0];
                                return (
                                    <div key={variant.variant_id} className="relative group">
                                        <button
                                            className={`w-full aspect-[9/16] rounded-lg overflow-hidden border-2 transition-all shadow-sm ${previewVariantId === variant.variant_id ||
                                                    (!previewVariantId && variant.is_default)
                                                    ? "border-indigo-500 ring-2 ring-indigo-300 transform scale-105"
                                                    : "border-slate-200 hover:border-indigo-400"
                                                }`}
                                            onClick={() => setPreviewVariantId(variant.variant_id)}
                                            title={variant.variant_name ?? variant.variant_type}
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
                                                className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-white text-rose-500 border border-slate-200 shadow-sm text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-rose-50 hover:border-rose-300"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (confirm("Delete this variant?")) {
                                                        deleteVariantMutation.mutate(variant.variant_id);
                                                    }
                                                }}
                                                disabled={deleteVariantMutation.isPending}
                                                title="Delete this variant"
                                            >
                                                &times;
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            {/* Sidebar */}
            <aside className="card space-y-6 self-start">
                <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-ink border-b pb-2">Traits</h4>
                    <div>
                        <p className="text-xs font-semibold text-slate-500">Gender</p>
                        <p className="text-sm text-ink capitalize bg-slate-50 px-2 py-1 rounded inline-block mt-1">{actor.gender ?? "Not specified"}</p>
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-500">Age Range</p>
                        <p className="text-sm text-ink bg-slate-50 px-2 py-1 rounded inline-block mt-1">{actor.age_range ?? "Not specified"}</p>
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-slate-500">Base Style</p>
                        <p className="text-xs text-ink bg-slate-50 px-2 py-1 rounded inline-block mt-1">
                            {actor.default_image_style_id ?? "default"}
                        </p>
                    </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                    <h4 className="text-sm font-semibold text-ink">Create Variant</h4>
                    <p className="mt-1 text-xs text-slate-500">
                        Generate a new look using the default identity.
                    </p>

                    <button
                        className="btn-secondary w-full text-xs mt-3 flex items-center justify-center gap-2"
                        onClick={() => setShowVariantForm(!showVariantForm)}
                    >
                        {showVariantForm ? "Cancel" : <span>&#43; New Variant</span>}
                    </button>

                    {showVariantForm && defaultVariant && (
                        <VariantForm
                            actor={actor}
                            baseVariant={defaultVariant}
                            onCreated={() => {
                                queryClient.invalidateQueries({ queryKey: ["actorLibrary"] });
                                setShowVariantForm(false);
                            }}
                        />
                    )}
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
        <div className="mt-4 space-y-3 p-3 bg-slate-50 rounded-lg border border-indigo-100">
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
                    placeholder="e.g., Wearing a red dress..."
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
                <p className="text-xs text-rose-500 mt-2">
                    {generateMutation.error instanceof Error
                        ? generateMutation.error.message
                        : "Failed to generate variant."}
                </p>
            )}
        </div>
    );
}

function GenerateTab({
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

    const getImageUrl = (url: string) => {
        if (url.startsWith("/media/")) {
            return `http://localhost:8000${url}`;
        }
        return url;
    };

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
                        <div className="relative h-[600px] w-full overflow-hidden rounded-xl bg-slate-100">
                            <img
                                src={getImageUrl(generationState.imageUrl)}
                                alt="Generated character"
                                className="mx-auto h-full object-contain"
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
                    <div className="mt-6 p-4 rounded-xl border border-green-200 bg-green-50 animate-fadeIn">
                        <h4 className="text-sm font-semibold text-green-800 flex items-center gap-2">
                            <span>&#10003;</span> Ready to Save
                        </h4>
                        <div className="mt-3 space-y-3">
                            <div>
                                <label className="text-xs font-semibold text-slate-500">Display Name *</label>
                                <input
                                    className="input mt-1 w-full"
                                    placeholder="e.g., Hero Character"
                                    value={displayName}
                                    onChange={(e) => setDisplayName(e.target.value)}
                                    autoFocus
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
                <p className="text-xs text-slate-500 mb-2">Define the look of your actor.</p>

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
    imageStyles,
    onImported
}: {
    imageStyles: StyleItem[];
    onImported: () => void;
}) {
    const [imageUrl, setImageUrl] = useState("");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [description, setDescription] = useState("");
    const [imageStyleId, setImageStyleId] = useState("default");
    const [gender, setGender] = useState("");
    const [ageRange, setAgeRange] = useState("");

    const importUrlMutation = useMutation({
        mutationFn: importActor,
        onSuccess: () => {
            onImported();
            resetForm();
        }
    });

    const importFileMutation = useMutation({
        mutationFn: importActorFromFile,
        onSuccess: () => {
            onImported();
            resetForm();
        }
    });

    const resetForm = () => {
        setImageUrl("");
        setSelectedFile(null);
        setPreviewUrl("");
        setDisplayName("");
        setDescription("");
        setGender("");
        setAgeRange("");
    };

    const handleImport = () => {
        const traits: CharacterTraitsInput = {};
        if (gender) traits.gender = gender;
        if (ageRange) traits.age_range = ageRange;

        if (selectedFile) {
            importFileMutation.mutate({
                file: selectedFile,
                displayName,
                description: description || null,
                traits,
                imageStyleId: imageStyleId !== "default" ? imageStyleId : null
            });
        } else {
            importUrlMutation.mutate({
                imageUrl,
                displayName,
                description: description || null,
                traits,
                imageStyleId: imageStyleId !== "default" ? imageStyleId : null
            });
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setImageUrl(""); // Clear URL input
            const objectUrl = URL.createObjectURL(file);
            setPreviewUrl(objectUrl);
        }
    };

    const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const url = e.target.value;
        setImageUrl(url);
        setSelectedFile(null); // Clear file selection
        setPreviewUrl(url);
    };

    const getImageUrl = (url: string) => {
        if (!url) return "";
        if (url.startsWith("blob:")) return url;
        if (url.startsWith("/media/")) {
            return `http://localhost:8000${url}`;
        }
        return url;
    };

    const isPending = importUrlMutation.isPending || importFileMutation.isPending;
    const isError = importUrlMutation.isError || importFileMutation.isError;
    const errorMessage = importUrlMutation.error?.message || importFileMutation.error?.message;

    return (
        <div className="grid gap-6 lg:grid-cols-[1fr,360px]">
            {/* Preview */}
            <div className="card">
                <h3 className="text-lg font-semibold text-ink">Image Preview</h3>
                <p className="text-xs text-slate-500 mt-1">
                    Upload an image or paste a URL to preview.
                </p>

                <div className="mt-6 rounded-2xl bg-white/80 p-4 shadow-soft">
                    {previewUrl ? (
                        <div className="relative h-[480px] w-full overflow-hidden rounded-xl bg-slate-100">
                            <img
                                src={getImageUrl(previewUrl)}
                                alt="Import preview"
                                className="mx-auto h-full object-contain"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).src = "";
                                    (e.target as HTMLImageElement).alt = "Failed to load image";
                                }}
                            />
                        </div>
                    ) : (
                        <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                            No image selected.
                        </div>
                    )}
                </div>
            </div>

            {/* Form */}
            <aside className="card">
                <h3 className="text-sm font-semibold text-ink">Import Details</h3>

                <div className="mt-4 space-y-4">
                    <div>
                        <label className="text-xs font-semibold text-slate-500">Image Source</label>
                        
                        {/* File Upload Button */}
                        <div className="mt-2">
                             <input
                                type="file"
                                accept="image/*"
                                onChange={handleFileSelect}
                                className="hidden"
                                id="file-upload"
                            />
                            <label 
                                htmlFor="file-upload"
                                className={`btn-secondary w-full text-xs flex items-center justify-center cursor-pointer ${selectedFile ? 'text-indigo-600 bg-indigo-50 border-indigo-200' : ''}`}
                            >
                                {selectedFile ? `File: ${selectedFile.name}` : "Upload from Computer"}
                            </label>
                        </div>
                        
                        <div className="relative flex py-2 items-center">
                            <div className="flex-grow border-t border-slate-200"></div>
                            <span className="flex-shrink mx-2 text-[10px] text-slate-400 font-medium">OR URL</span>
                            <div className="flex-grow border-t border-slate-200"></div>
                        </div>

                        <input
                            className="input w-full text-sm"
                            placeholder="https://example.com/image.png"
                            value={imageUrl}
                            onChange={handleUrlChange}
                            disabled={!!selectedFile}
                        />
                         {selectedFile && (
                            <button 
                                className="text-[10px] text-slate-500 mt-1 underline"
                                onClick={() => {
                                    setSelectedFile(null);
                                    setPreviewUrl("");
                                }}
                            >
                                Clear file to use URL
                            </button>
                        )}
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
                        disabled={isPending || (!imageUrl.trim() && !selectedFile) || !displayName.trim()}
                    >
                        {isPending ? "Importing..." : "Import to Library"}
                    </button>

                    {isError && (
                        <p className="text-xs text-rose-500">
                             {errorMessage || "Failed to import character."}
                        </p>
                    )}
                </div>
            </aside>
        </div>
    );
}
