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
  deleteCharacterRef
} from "@/lib/api/queries";
import type { Character, CharacterRef } from "@/lib/api/types";

export default function CharacterStudioPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [storyId, setStoryId] = useState("");

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

  return (
    <section className="max-w-5xl mx-auto">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Character Design</h1>
            <p className="mt-1 text-slate-500">
              Generate reference images for each character. Select the best one for visual consistency.
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

        {/* Character Cards */}
        <div className="mt-8 space-y-6">
          {charactersQuery.isLoading && (
            <div className="text-center py-12 text-slate-500">Loading characters...</div>
          )}

          {charactersQuery.data?.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-500">No characters found.</p>
              <Link href="/studio/story" className="btn-ghost text-sm mt-4 inline-block">
                &larr; Generate story first
              </Link>
            </div>
          )}

          {charactersQuery.data?.map((character) => (
            <CharacterCard key={character.character_id} character={character} />
          ))}
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

function CharacterCard({ character }: { character: Character }) {
  const queryClient = useQueryClient();

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

  const deleteRefMutation = useMutation({
    mutationFn: deleteCharacterRef,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characterRefs", character.character_id] });
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
      countPerType: 2
    });
  };

  const getImageUrl = (ref: CharacterRef) => {
    if (ref.image_url.startsWith("/media/")) {
      return `http://localhost:8000${ref.image_url}`;
    }
    return ref.image_url;
  };

  const primaryRef = refsQuery.data?.find((r) => r.is_primary);
  const hasApprovedRef = character.approved;

  return (
    <div className={`card ${hasApprovedRef ? "ring-2 ring-green-500" : ""}`}>
      <div className="flex items-start gap-4">
        {/* Character Avatar / Primary Ref */}
        <div className="flex-shrink-0">
          {primaryRef ? (
            <img
              src={getImageUrl(primaryRef)}
              alt={character.name}
              className="w-20 h-20 rounded-lg object-cover"
            />
          ) : (
            <div className="w-20 h-20 rounded-lg bg-slate-200 flex items-center justify-center">
              <span className="text-2xl font-bold text-slate-400">
                {character.name.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
        </div>

        {/* Character Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-ink">{character.name}</h3>
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
            <p className="mt-1 text-sm text-slate-600">{character.description}</p>
          )}
          {character.identity_line && (
            <p className="mt-1 text-xs text-slate-500 italic">{character.identity_line}</p>
          )}
        </div>

        {/* Action Button */}
        <div className="flex-shrink-0">
          <button
            className="btn-primary text-sm"
            onClick={handleGenerate}
            disabled={generateRefsMutation.isPending}
          >
            {generateRefsMutation.isPending ? "Generating..." : "Generate Images"}
          </button>
        </div>
      </div>

      {/* Reference Images Grid */}
      {refsQuery.data && refsQuery.data.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-100">
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

                {/* Delete button */}
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

                {/* Selected indicator */}
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

      {/* Error messages */}
      {generateRefsMutation.isError && (
        <p className="mt-3 text-sm text-rose-500">
          Failed to generate images. Make sure the character has a description.
        </p>
      )}
    </div>
  );
}
