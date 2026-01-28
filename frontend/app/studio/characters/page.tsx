"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchCharacters,
  fetchProjects,
  fetchStories,
  fetchCharacterRefs,
  generateCharacterRefs,
  approveCharacterRef,
  setPrimaryCharacterRef,
  deleteCharacterRef,
  updateCharacter,
  approveCharacter
} from "@/lib/api/queries";
import type { Character, CharacterRef } from "@/lib/api/types";

export default function CharacterStudioPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [storyId, setStoryId] = useState("");
  const [selectedCharacterId, setSelectedCharacterId] = useState("");

  // Queries
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects
  });

  const storiesQuery = useQuery({
    queryKey: ["stories", projectId],
    queryFn: () => fetchStories(projectId),
    enabled: projectId.length > 0
  });

  const charactersQuery = useQuery({
    queryKey: ["characters", storyId],
    queryFn: () => fetchCharacters(storyId),
    enabled: storyId.length > 0
  });

  // Load from localStorage
  useEffect(() => {
    const storedProjectId = window.localStorage.getItem("lastProjectId") ?? "";
    const storedStoryId = window.localStorage.getItem("lastStoryId") ?? "";
    if (storedProjectId) setProjectId(storedProjectId);
    if (storedStoryId) setStoryId(storedStoryId);
  }, []);

  useEffect(() => {
    if (projectId) window.localStorage.setItem("lastProjectId", projectId);
  }, [projectId]);

  useEffect(() => {
    if (storyId) window.localStorage.setItem("lastStoryId", storyId);
  }, [storyId]);

  // Check if all characters have approved primary refs
  const allCharactersReady = charactersQuery.data?.every((c) => c.approved) ?? false;

  useEffect(() => {
    if (!charactersQuery.data || charactersQuery.data.length === 0) return;
    if (!selectedCharacterId) {
      setSelectedCharacterId(charactersQuery.data[0].character_id);
    }
  }, [charactersQuery.data, selectedCharacterId]);

  if (!storyId) {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink">Character Design</h1>
          <p className="mt-2 text-slate-500">Select a project and story to design characters.</p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-ink">Project</label>
              <select
                className="input w-full"
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value);
                  setStoryId("");
                }}
              >
                <option value="">Select project</option>
                {projectsQuery.data?.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-ink">Story</label>
              <select
                className="input w-full"
                value={storyId}
                onChange={(e) => setStoryId(e.target.value)}
                disabled={!projectId}
              >
                <option value="">Select story</option>
                {storiesQuery.data?.map((story) => (
                  <option key={story.story_id} value={story.story_id}>
                    {story.title}
                  </option>
                ))}
              </select>
            </div>
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

  const selectedCharacter = charactersQuery.data?.find(
    (character) => character.character_id === selectedCharacterId
  );

  return (
    <section className="max-w-6xl mx-auto">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Character Design</h1>
            <p className="mt-1 text-slate-500">
              Select a character on the left, then generate reference images in the center.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              className="input text-sm"
              value={storyId}
              onChange={(e) => setStoryId(e.target.value)}
            >
              {storiesQuery.data?.map((story) => (
                <option key={story.story_id} value={story.story_id}>
                  {story.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[260px,1fr]">
          <aside className="space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Characters</p>
            {charactersQuery.isLoading && (
              <div className="text-sm text-slate-500">Loading characters...</div>
            )}
            {charactersQuery.data?.length === 0 && (
              <div className="text-sm text-slate-500">
                No characters found. Generate a story first.
              </div>
            )}
            {charactersQuery.data?.map((character) => (
              <button
                key={character.character_id}
                className={`w-full text-left rounded-xl border px-3 py-2 transition ${
                  character.character_id === selectedCharacterId
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-slate-200 bg-white/70 hover:border-indigo-200"
                }`}
                onClick={() => setSelectedCharacterId(character.character_id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-ink">{character.name}</p>
                    <p className="text-xs text-slate-500 capitalize">{character.role}</p>
                  </div>
                  {character.approved && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                      Ready
                    </span>
                  )}
                </div>
                <p className="mt-2 text-xs text-slate-500 line-clamp-3">
                  {character.description || character.identity_line || "No description yet."}
                </p>
              </button>
            ))}
          </aside>

          <div>
            {!selectedCharacter && (
              <div className="card text-sm text-slate-500">Select a character to begin.</div>
            )}
            {selectedCharacter && <CharacterDetail character={selectedCharacter} />}
          </div>
        </div>

        {/* Proceed Button */}
        {charactersQuery.data && charactersQuery.data.length > 0 && (
          <div className="mt-8 pt-6 border-t border-slate-200">
            <Link
              href="/studio/scenes"
              className={`w-full py-3 text-base text-center block ${
                allCharactersReady
                  ? "btn-primary"
                  : "btn-ghost opacity-50 cursor-not-allowed"
              }`}
              onClick={(e) => {
                if (!allCharactersReady) e.preventDefault();
              }}
            >
              {allCharactersReady
                ? "Proceed to Scene Generation"
                : "Select a reference for each character to proceed"}
            </Link>
            <p className="mt-3 text-xs text-slate-500 text-center">
              Next: Generate scene images using your character references
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function CharacterDetail({ character }: { character: Character }) {
  const queryClient = useQueryClient();
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [identityDraft, setIdentityDraft] = useState("");

  // Fetch refs for this character
  const refsQuery = useQuery({
    queryKey: ["characterRefs", character.character_id],
    queryFn: () => fetchCharacterRefs(character.character_id)
  });

  const generateRefsMutation = useMutation({
    mutationFn: generateCharacterRefs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characterRefs", character.character_id] });
    }
  });

  const approveRefMutation = useMutation({
    mutationFn: approveCharacterRef,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characterRefs", character.character_id] });
      queryClient.invalidateQueries({ queryKey: ["characters"] });
    }
  });

  const setPrimaryRefMutation = useMutation({
    mutationFn: setPrimaryCharacterRef,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characterRefs", character.character_id] });
      queryClient.invalidateQueries({ queryKey: ["characters"] });
    }
  });

  const approveCharacterMutation = useMutation({
    mutationFn: approveCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
    }
  });

  const deleteRefMutation = useMutation({
    mutationFn: deleteCharacterRef,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characterRefs", character.character_id] });
    }
  });

  const updateCharacterMutation = useMutation({
    mutationFn: updateCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
    }
  });

  const handleSelectAsReference = async (ref: CharacterRef) => {
    // Approve first, then set as primary
    await approveRefMutation.mutateAsync({
      characterId: character.character_id,
      referenceImageId: ref.reference_image_id
    });
    await setPrimaryRefMutation.mutateAsync({
      characterId: character.character_id,
      referenceImageId: ref.reference_image_id
    });
    await approveCharacterMutation.mutateAsync(character.character_id);
  };

  const handleDelete = (ref: CharacterRef) => {
    deleteRefMutation.mutate({
      characterId: character.character_id,
      referenceImageId: ref.reference_image_id
    });
  };

  const handleGenerate = () => {
    generateRefsMutation.mutate({
      characterId: character.character_id,
      refTypes: ["face"],
      countPerType: 1
    });
  };

  const getImageUrl = (ref: CharacterRef) => {
    if (ref.image_url.startsWith("/media/")) {
      return `http://localhost:8000${ref.image_url}`;
    }
    return ref.image_url;
  };

  const primaryRef = refsQuery.data?.find((r) => r.is_primary);
  const previewRef = primaryRef ?? refsQuery.data?.[0];
  const hasApprovedRef = character.approved;
  const hasPrompt = Boolean(character.description || character.identity_line);

  useEffect(() => {
    setDescriptionDraft(character.description ?? "");
    setIdentityDraft(character.identity_line ?? "");
  }, [character.character_id, character.description, character.identity_line]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,320px]">
      <div className={`card ${hasApprovedRef ? "ring-2 ring-green-500" : ""}`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-ink">{character.name}</h3>
            <p className="text-xs text-slate-500 capitalize">{character.role}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn-ghost text-sm"
              onClick={() => approveCharacterMutation.mutate(character.character_id)}
              disabled={approveCharacterMutation.isPending}
            >
              {approveCharacterMutation.isPending ? "Skipping..." : "Skip Reference Image"}
            </button>
            <button
              className="btn-primary text-sm"
              onClick={handleGenerate}
              disabled={generateRefsMutation.isPending || !hasPrompt}
            >
              {generateRefsMutation.isPending ? "Generating..." : "Generate Image"}
            </button>
          </div>
        </div>
        {!hasPrompt && (
          <p className="mt-2 text-xs text-rose-500">
            Add a description or identity line before generating images.
          </p>
        )}
        <div className="mt-6 flex items-center justify-center rounded-2xl bg-white/80 p-4 shadow-soft">
          {previewRef ? (
            <img
              src={getImageUrl(previewRef)}
              alt={character.name}
              className="max-h-[420px] w-full rounded-xl object-contain"
            />
          ) : (
            <div className="flex h-[360px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              No image yet.
            </div>
          )}
        </div>

        {refsQuery.data && refsQuery.data.length > 0 && (
          <div className="mt-6">
            <p className="text-xs text-slate-500 mb-3">
              Click an image to select it as the reference for this character.
            </p>
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
              {refsQuery.data.map((ref) => (
                <div key={ref.reference_image_id} className="relative group">
                  <button
                    className={`w-full aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                      ref.is_primary
                        ? "border-green-500 ring-2 ring-green-300"
                        : "border-slate-200 hover:border-indigo-400"
                    }`}
                    onClick={() => handleSelectAsReference(ref)}
                    disabled={approveRefMutation.isPending || setPrimaryRefMutation.isPending}
                  >
                    <img
                      src={getImageUrl(ref)}
                      alt="Character reference"
                      className="w-full h-full object-cover"
                    />
                  </button>

                  <button
                    className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-red-500 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(ref);
                    }}
                    disabled={deleteRefMutation.isPending}
                    title="Delete this image"
                  >
                    &times;
                  </button>

                  {ref.is_primary && (
                    <div className="absolute bottom-1 left-1 right-1 bg-green-500 text-white text-[10px] text-center rounded py-0.5">
                      Selected
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {generateRefsMutation.isError && (
          <p className="mt-3 text-sm text-rose-500">
            {generateRefsMutation.error instanceof Error
              ? generateRefsMutation.error.message
              : "Failed to generate images."}
          </p>
        )}
      </div>

      <aside className="card">
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 capitalize">
            {character.role}
          </span>
          {hasApprovedRef && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
              Ready
            </span>
          )}
        </div>
        {character.description && (
          <p className="mt-2 text-sm text-slate-600">{character.description}</p>
        )}
        {character.identity_line && (
          <p className="mt-2 text-xs text-slate-500 italic">{character.identity_line}</p>
        )}

        <div className="mt-5 space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-500">Description</label>
            <textarea
              className="textarea mt-2 w-full min-h-[90px]"
              placeholder="Describe the character to help the image generator."
              value={descriptionDraft}
              onChange={(event) => setDescriptionDraft(event.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-500">Identity Line</label>
            <textarea
              className="textarea mt-2 w-full min-h-[90px]"
              placeholder="Optional single-line identity summary."
              value={identityDraft}
              onChange={(event) => setIdentityDraft(event.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn-ghost text-xs"
              onClick={() => {
                setDescriptionDraft(character.description ?? "");
                setIdentityDraft(character.identity_line ?? "");
              }}
              disabled={updateCharacterMutation.isPending}
            >
              Reset
            </button>
            <button
              className="btn-primary text-xs"
              onClick={() => {
                updateCharacterMutation.mutate({
                  characterId: character.character_id,
                  description: descriptionDraft,
                  identityLine: identityDraft
                });
              }}
              disabled={updateCharacterMutation.isPending}
            >
              {updateCharacterMutation.isPending ? "Saving..." : "Save"}
            </button>
          </div>
          {updateCharacterMutation.isError && (
            <span className="text-xs text-rose-500">Failed to save.</span>
          )}
          {updateCharacterMutation.isSuccess && (
            <span className="text-xs text-green-600">Saved</span>
          )}
        </div>
      </aside>
    </div>
  );
}
