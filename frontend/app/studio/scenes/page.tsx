"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchStories,
  fetchStory,
  fetchScenes,
  fetchSceneArtifacts,
  fetchSceneRenders,
  generateSceneFull
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
  const [selectedSceneId, setSelectedSceneId] = useState("");
  const [promptOverride, setPromptOverride] = useState<string | null>(null);

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

  const storyQuery = useQuery({
    queryKey: ["story", storyId],
    queryFn: () => fetchStory(storyId),
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

  useEffect(() => {
    if (!scenesQuery.data || scenesQuery.data.length === 0) return;
    if (!selectedSceneId) {
      setSelectedSceneId(scenesQuery.data[0].scene_id);
    }
  }, [scenesQuery.data, selectedSceneId]);

  const selectedScene = useMemo(
    () => scenesQuery.data?.find((scene) => scene.scene_id === selectedSceneId),
    [scenesQuery.data, selectedSceneId]
  );

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
    <section className="max-w-6xl mx-auto">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Scene Generation</h1>
            <p className="mt-1 text-slate-500">
              Select a scene on the left, then generate or review its image in the center.
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

        <div className="mt-8 grid gap-6 lg:grid-cols-[260px,1fr,320px]">
          <aside className="space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Scenes</p>
            {scenesQuery.isLoading && (
              <div className="text-sm text-slate-500">Loading scenes...</div>
            )}
            {scenesQuery.data?.length === 0 && (
              <div className="text-sm text-slate-500">
                No scenes found. Generate a story first.
              </div>
            )}
            {scenesQuery.data?.map((scene, index) => (
              <button
                key={scene.scene_id}
                className={`w-full text-left rounded-xl border px-3 py-2 transition ${
                  scene.scene_id === selectedSceneId
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-slate-200 bg-white/70 hover:border-indigo-200"
                }`}
                onClick={() => setSelectedSceneId(scene.scene_id)}
              >
                <p className="text-sm font-semibold text-ink">Scene {index + 1}</p>
                <p className="mt-1 text-xs text-slate-500 line-clamp-3">
                  {scene.source_text}
                </p>
              </button>
            ))}
          </aside>

          <div>
            {!selectedScene && (
              <div className="card text-sm text-slate-500">Select a scene to begin.</div>
            )}
            {selectedScene && (
              <SceneDetail
                scene={selectedScene}
                storyStyle={storyQuery.data?.default_story_style}
                imageStyle={storyQuery.data?.default_image_style}
                promptOverride={promptOverride}
              />
            )}
          </div>

          <aside className="card">
            {selectedScene ? (
              <ScenePromptPanel
                sceneId={selectedScene.scene_id}
                onPromptOverrideChange={setPromptOverride}
              />
            ) : (
              <p className="text-sm text-slate-500">Select a scene to see details.</p>
            )}
          </aside>
        </div>

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

function SceneDetail({
  scene,
  storyStyle,
  imageStyle,
  promptOverride
}: {
  scene: Scene;
  storyStyle?: string;
  imageStyle?: string;
  promptOverride?: string | null;
}) {
  const queryClient = useQueryClient();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [imageLoadError, setImageLoadError] = useState("");
  const [waitingForImage, setWaitingForImage] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [selectedPromptVersion, setSelectedPromptVersion] = useState<number | null>(null);

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
    mutationFn: generateSceneFull,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["renders", scene.scene_id] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", scene.scene_id] });
      setIsGenerating(false);
      setWaitingForImage(true);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Generation failed");
      setIsGenerating(false);
    }
  });

  const latestRenderFromRenders = rendersQuery.data
    ? getLatestArtifact(rendersQuery.data, "render_result")
    : null;
  const latestRenderFromArtifacts = artifactsQuery.data
    ? getLatestArtifact(artifactsQuery.data, "render_result")
    : null;
  const latestRender = latestRenderFromRenders ?? latestRenderFromArtifacts;

  const hasSemantics = artifactsQuery.data
    ? !!getLatestArtifact(artifactsQuery.data, "panel_semantics")
    : false;

  const handleGenerate = async () => {
    setError("");
    setIsGenerating(true);
    const normalizedPromptOverride = promptOverride?.trim()
      ? promptOverride.trim()
      : null;
    try {
      await renderMutation.mutateAsync({
        sceneId: scene.scene_id,
        panelCount: 4,
        styleId: scene.image_style_override ?? imageStyle ?? "default",
        genre: scene.story_style_override ?? storyStyle ?? null,
        promptOverride: normalizedPromptOverride
      });
    } catch {
      // Error handled in mutation
    }
  };

  const getImageUrl = (url: string) => {
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("/media/")) return `http://localhost:8000${url}`;
    if (url.startsWith("media/")) return `http://localhost:8000/${url}`;
    if (url.startsWith("/")) return `http://localhost:8000${url}`;
    return `http://localhost:8000/${url}`;
  };

  const extractImageUrl = (payload: Artifact["payload"] | undefined) => {
    if (!payload || typeof payload !== "object") return null;
    const maybe = payload as Record<string, any>;
    return (
      maybe.image_url ||
      maybe.url ||
      maybe.image?.url ||
      maybe.image?.image_url ||
      maybe.output?.image_url ||
      maybe.result?.image_url ||
      maybe.result?.url ||
      maybe.images?.[0]?.url ||
      maybe.images?.[0]?.image_url ||
      null
    );
  };

  const rawImageUrl = extractImageUrl(latestRender?.payload);

  const imageUrl = rawImageUrl ? getImageUrl(String(rawImageUrl)) : null;

  useEffect(() => {
    setImageLoadError("");
    setError("");
    setIsGenerating(false);
    setWaitingForImage(false);
    setZoom(1);
    setSelectedPrompt(null);
    setSelectedPromptVersion(null);
  }, [scene.scene_id]);

  useEffect(() => {
    if (waitingForImage && imageUrl) {
      setWaitingForImage(false);
      setImageLoadError("");
    }
  }, [waitingForImage, imageUrl]);

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-ink">Scene Image</h3>
          <p className="text-xs text-slate-500">
            {hasSemantics
              ? "Scene planning ready."
              : "Scene planning not complete. This was generated during story creation."}
          </p>
        </div>
        <button
          className="btn-primary text-sm"
          onClick={handleGenerate}
          disabled={isGenerating || waitingForImage}
        >
          {isGenerating || waitingForImage
            ? "Generating..."
            : imageUrl
              ? "Generate Another"
              : "Generate Image"}
        </button>
      </div>

      <div className="mt-6 flex items-center justify-center rounded-2xl bg-white/80 p-4 shadow-soft">
        <div className="w-full">
          <div className="mb-3 flex items-center justify-end gap-2">
            <button
              className="btn-ghost text-xs"
              onClick={() => setZoom((prev) => Math.max(0.6, Number((prev - 0.1).toFixed(2))))}
              disabled={zoom <= 0.6}
            >
              −
            </button>
            <span className="text-xs text-slate-500 w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              className="btn-ghost text-xs"
              onClick={() => setZoom((prev) => Math.min(2, Number((prev + 0.1).toFixed(2))))}
              disabled={zoom >= 2}
            >
              +
            </button>
          </div>
          {imageUrl && !imageLoadError ? (
            <div className="relative h-[620px] w-full overflow-auto rounded-xl bg-slate-100">
              <img
                src={imageUrl}
                alt="Scene render"
                className="mx-auto rounded-xl object-contain"
                style={{ transform: `scale(${zoom})`, transformOrigin: "top center" }}
                onError={() => setImageLoadError("Unable to load render image.")}
                onLoad={() => {
                  setImageLoadError("");
                  setWaitingForImage(false);
                }}
              />
            </div>
          ) : (
            <div className="flex h-[520px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              {imageLoadError ||
                (waitingForImage
                  ? "Generating image... This can take a minute."
                  : "No scene image yet. Click Generate Image to run planning + render.")}
            </div>
          )}
        </div>
      </div>

      {latestRender && !imageUrl && !imageLoadError && (
        <p className="mt-2 text-xs text-slate-400">
          Render artifact missing image URL.
        </p>
      )}

      {(error || imageLoadError) && (
        <p className="mt-2 text-xs text-rose-500">{error || imageLoadError}</p>
      )}

      {rendersQuery.data && rendersQuery.data.length > 1 && (
        <div className="mt-6">
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
                <button
                  key={render.artifact_id}
                  type="button"
                  className="group"
                  onClick={() => {
                    const prompt =
                      typeof render.payload?.prompt === "string"
                        ? render.payload.prompt
                        : null;
                    setSelectedPrompt(prompt);
                    setSelectedPromptVersion(render.version);
                  }}
                >
                  <img
                    src={url}
                    alt={`Version ${render.version}`}
                    className="w-16 h-28 rounded object-cover opacity-60 hover:opacity-100 cursor-pointer"
                  />
                </button>
              );
            })}
          </div>
          {selectedPromptVersion && (
            <div className="mt-3 rounded-xl border border-slate-200 bg-white/80 p-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-ink">
                  Prompt for version {selectedPromptVersion}
                </p>
                <button
                  type="button"
                  className="text-[11px] font-semibold text-slate-400 hover:text-slate-500"
                  onClick={() => {
                    setSelectedPrompt(null);
                    setSelectedPromptVersion(null);
                  }}
                >
                  Hide
                </button>
              </div>
              {selectedPrompt ? (
                <p className="mt-2 text-[11px] text-slate-600 whitespace-pre-wrap">
                  {selectedPrompt}
                </p>
              ) : (
                <p className="mt-2 text-[11px] text-slate-400">
                  Prompt not available for this version.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScenePromptPanel({
  sceneId,
  onPromptOverrideChange
}: {
  sceneId: string;
  onPromptOverrideChange: (prompt: string | null) => void;
}) {
  const artifactsQuery = useQuery({
    queryKey: ["artifacts", sceneId],
    queryFn: () => fetchSceneArtifacts(sceneId),
    enabled: sceneId.length > 0
  });

  const latestRenderSpec = artifactsQuery.data
    ? getLatestArtifact(artifactsQuery.data, "render_spec")
    : null;
  const renderPrompt =
    typeof latestRenderSpec?.payload?.prompt === "string"
      ? latestRenderSpec.payload.prompt
      : "";

  const [draft, setDraft] = useState("");
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setDraft(renderPrompt);
    setIsDirty(false);
    onPromptOverrideChange(null);
  }, [sceneId, renderPrompt, onPromptOverrideChange]);

  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">Scene Prompt</h3>
        <button
          type="button"
          className="text-[11px] font-semibold text-indigo-500 hover:text-indigo-600"
          onClick={() => {
            setDraft(renderPrompt);
            setIsDirty(false);
            onPromptOverrideChange(null);
          }}
          disabled={!renderPrompt}
        >
          Reset to auto
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-500">Edit the prompt used to generate this scene image.</p>
      <textarea
        className="mt-3 h-[360px] w-full rounded-xl border border-slate-200 bg-white/80 p-3 text-xs text-slate-700 shadow-soft focus:outline-none focus:ring-2 focus:ring-indigo-200"
        value={draft}
        onChange={(e) => {
          const value = e.target.value;
          setDraft(value);
          setIsDirty(true);
          onPromptOverrideChange(value);
        }}
        placeholder="Generate an image to see the auto prompt, or type your own."
      />
      <p className="mt-2 text-[11px] text-slate-400">
        {isDirty ? "Custom prompt will be used on Generate Image." : "Auto prompt loaded."}
      </p>
    </>
  );
}
