"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchStories,
  fetchScenes,
  fetchSceneArtifacts,
  fetchSceneRenders,
  generateRender
} from "@/lib/api/queries";
import type { Scene, Artifact } from "@/lib/api/types";

function getLatestArtifact(artifacts: Artifact[], type: string) {
  return artifacts
    .filter((artifact) => artifact.type === type)
    .sort((a, b) => b.version - a.version)[0];
}

export default function ScenesPage() {
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

  const scenesQuery = useQuery({
    queryKey: ["scenes", storyId],
    queryFn: () => fetchScenes(storyId),
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

  // Check if all scenes have approved renders
  const allScenesReady = false; // TODO: track scene approval state

  if (!storyId) {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink">Scene Generation</h1>
          <p className="mt-2 text-slate-500">Select a project and story to generate scene images.</p>

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
            <Link href="/studio/characters" className="btn-ghost text-sm">
              &larr; Back to Character Design
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
            <h1 className="text-2xl font-bold text-ink">Scene Generation</h1>
            <p className="mt-1 text-slate-500">
              Generate images for each scene. Select the best version for your webtoon.
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

        {/* Scene Cards */}
        <div className="mt-8 space-y-6">
          {scenesQuery.isLoading && (
            <div className="text-center py-12 text-slate-500">Loading scenes...</div>
          )}

          {scenesQuery.data?.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-500">No scenes found.</p>
              <Link href="/studio/story" className="btn-ghost text-sm mt-4 inline-block">
                &larr; Generate story first
              </Link>
            </div>
          )}

          {scenesQuery.data?.map((scene, index) => (
            <SceneCard key={scene.scene_id} scene={scene} index={index} />
          ))}
        </div>

        {/* Proceed Button */}
        {scenesQuery.data && scenesQuery.data.length > 0 && (
          <div className="mt-8 pt-6 border-t border-slate-200">
            <Link
              href="/studio/dialogue"
              className="btn-primary w-full py-3 text-base text-center block"
            >
              Proceed to Dialogue Editor
            </Link>
            <p className="mt-3 text-xs text-slate-500 text-center">
              Next: Add dialogue bubbles to your scene images
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function SceneCard({ scene, index }: { scene: Scene; index: number }) {
  const queryClient = useQueryClient();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");

  // Fetch renders for this scene
  const rendersQuery = useQuery({
    queryKey: ["renders", scene.scene_id],
    queryFn: () => fetchSceneRenders(scene.scene_id)
  });

  // Fetch artifacts to check if planning is done
  const artifactsQuery = useQuery({
    queryKey: ["artifacts", scene.scene_id],
    queryFn: () => fetchSceneArtifacts(scene.scene_id)
  });

  const renderMutation = useMutation({
    mutationFn: generateRender,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["renders", scene.scene_id] });
      setIsGenerating(false);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Generation failed");
      setIsGenerating(false);
    }
  });

  const latestRender = rendersQuery.data
    ? getLatestArtifact(rendersQuery.data, "render_result")
    : null;

  const hasSemantics = artifactsQuery.data
    ? !!getLatestArtifact(artifactsQuery.data, "panel_semantics")
    : false;

  const handleGenerate = async () => {
    setError("");
    setIsGenerating(true);
    try {
      await renderMutation.mutateAsync(scene.scene_id);
    } catch {
      // Error handled in mutation
    }
  };

  const getImageUrl = (url: string) => {
    if (url.startsWith("/media/")) {
      return `http://localhost:8000${url}`;
    }
    return url;
  };

  const imageUrl = latestRender?.payload?.image_url
    ? getImageUrl(String(latestRender.payload.image_url))
    : null;

  return (
    <div className="card">
      <div className="flex gap-6">
        {/* Scene Image */}
        <div className="flex-shrink-0 w-48">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={`Scene ${index + 1}`}
              className="w-full aspect-[9/16] rounded-lg object-cover shadow-sm"
            />
          ) : (
            <div className="w-full aspect-[9/16] rounded-lg bg-gradient-to-b from-slate-200 to-slate-100 flex items-center justify-center">
              <span className="text-slate-400 text-sm">No image yet</span>
            </div>
          )}
        </div>

        {/* Scene Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
              <span className="text-sm font-bold text-indigo-600">{index + 1}</span>
            </div>
            <h3 className="text-lg font-semibold text-ink">Scene {index + 1}</h3>
            {imageUrl && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                Generated
              </span>
            )}
          </div>

          {/* Scene Description */}
          <div className="mt-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              {scene.source_text.length > 400
                ? scene.source_text.slice(0, 400) + "..."
                : scene.source_text}
            </p>
          </div>

          {/* Actions */}
          <div className="mt-4 flex items-center gap-3">
            <button
              className="btn-primary text-sm"
              onClick={handleGenerate}
              disabled={isGenerating || !hasSemantics}
            >
              {isGenerating ? "Generating..." : imageUrl ? "Generate Another" : "Generate Image"}
            </button>

            {imageUrl && (
              <button className="btn-ghost text-sm" disabled>
                Select as Final
              </button>
            )}
          </div>

          {!hasSemantics && (
            <p className="mt-2 text-xs text-amber-600">
              Scene planning not complete. This was generated during story creation.
            </p>
          )}

          {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}

          {/* Render versions */}
          {rendersQuery.data && rendersQuery.data.length > 1 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-500 mb-2">
                Previous versions ({rendersQuery.data.length})
              </p>
              <div className="flex gap-2 overflow-x-auto">
                {rendersQuery.data.slice(1, 5).map((render) => {
                  const url = render.payload?.image_url
                    ? getImageUrl(String(render.payload.image_url))
                    : null;
                  if (!url) return null;
                  return (
                    <img
                      key={render.artifact_id}
                      src={url}
                      alt={`Version ${render.version}`}
                      className="w-16 h-28 rounded object-cover opacity-60 hover:opacity-100 cursor-pointer"
                    />
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
