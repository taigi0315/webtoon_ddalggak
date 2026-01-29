"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchStories,
  fetchScenes,
  fetchSceneRenders,
  fetchDialogueSuggestions,
  fetchDialogueLayer,
  createDialogueLayer,
  updateDialogueLayer,
  fetchStory,
  fetchEpisodes,
  createEpisode,
  setEpisodeScenes,
  createEpisodeExport,
  finalizeExport,
  generateVideoExport,
  fetchExport
} from "@/lib/api/queries";
import type { Artifact, DialogueSuggestion, Scene } from "@/lib/api/types";

function getLatestArtifact(artifacts: Artifact[], type: string) {
  return artifacts
    .filter((artifact) => artifact.type === type)
    .sort((a, b) => b.version - a.version)[0];
}

function getImageUrl(url: string) {
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/media/")) return `http://localhost:8000${url}`;
  if (url.startsWith("media/")) return `http://localhost:8000/${url}`;
  if (url.startsWith("/")) return `http://localhost:8000${url}`;
  return `http://localhost:8000/${url}`;
}

export default function DialogueEditorPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [storyId, setStoryId] = useState("");
  const [selectedSceneId, setSelectedSceneId] = useState("");
  const [bubbles, setBubbles] = useState<DialogueBubble[]>([]);
  const [activeBubbleId, setActiveBubbleId] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<"select" | "speech" | "tail" | "delete">(
    "select"
  );
  const [zoom, setZoom] = useState(1);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState("");
  const [videoStatus, setVideoStatus] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [lastExportId, setLastExportId] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [autoOpened, setAutoOpened] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [pollSeconds, setPollSeconds] = useState(0);
  const scenesRowRef = useRef<HTMLDivElement | null>(null);
  const sceneCardRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [scenesOverflow, setScenesOverflow] = useState(false);

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

  const episodesQuery = useQuery({
    queryKey: ["episodes", storyId],
    queryFn: () => fetchEpisodes(storyId),
    enabled: storyId.length > 0
  });

  const dialogueLayerQuery = useQuery({
    queryKey: ["dialogue-layer", selectedSceneId],
    queryFn: () => fetchDialogueLayer(selectedSceneId),
    enabled: selectedSceneId.length > 0
  });

  const saveLayerMutation = useMutation({
    mutationFn: async () => {
      if (!selectedSceneId) return null;
      const validBubbles = bubbles.filter((bubble) => bubble.text.trim().length > 0);
      if (validBubbles.length === 0) {
        throw new Error("Add at least one dialogue bubble before saving.");
      }
      const payloadBubbles = validBubbles.map((bubble) => ({
        bubble_id: bubble.id,
        panel_id: bubble.panelId,
        text: bubble.text,
        position: bubble.position,
        size: bubble.size,
        tail: bubble.tail ?? null
      }));
      if (dialogueLayerQuery.data?.dialogue_id) {
        return updateDialogueLayer({
          dialogueId: dialogueLayerQuery.data.dialogue_id,
          bubbles: payloadBubbles
        });
      }
      return createDialogueLayer({ sceneId: selectedSceneId, bubbles: payloadBubbles });
    },
    onSuccess: () => {
      if (!selectedSceneId) return;
      queryClient.invalidateQueries({ queryKey: ["dialogue-layer", selectedSceneId] });
      setSaveError(null);
    },
    onError: (err) => {
      setSaveError(err instanceof Error ? err.message : "Unable to save dialogue layer.");
    }
  });

  const createEpisodeMutation = useMutation({
    mutationFn: async () => {
      if (!storyId || !storyQuery.data) return null;
      return createEpisode({
        storyId,
        title: `${storyQuery.data.title} Episode`,
        defaultStoryStyle: storyQuery.data.default_story_style,
        defaultImageStyle: storyQuery.data.default_image_style
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["episodes", storyId] });
    }
  });

  const generateVideoMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEpisodeId) throw new Error("Select an episode");
      if (!scenesQuery.data || scenesQuery.data.length === 0) {
        throw new Error("No scenes found for this story");
      }
      const selectedEpisode = episodesQuery.data?.find(
        (episode: any) => episode.episode_id === selectedEpisodeId
      );
      const sceneIds =
        selectedEpisode?.scene_ids_ordered?.length > 0
          ? selectedEpisode.scene_ids_ordered
          : scenesQuery.data.map((scene) => scene.scene_id);
      if (!selectedEpisode?.scene_ids_ordered?.length) {
        await setEpisodeScenes({ episodeId: selectedEpisodeId, sceneIds });
        await queryClient.invalidateQueries({ queryKey: ["episodes", storyId] });
      }
      const exportJob = await createEpisodeExport(selectedEpisodeId);
      const finalized = await finalizeExport(exportJob.export_id);
      const videoJob = await generateVideoExport(finalized.export_id);
      setLastExportId(videoJob.export_id);
      return videoJob;
    },
    onSuccess: () => {
      setVideoStatus("processing");
      setVideoError(null);
      setAutoOpened(false);
      setPollSeconds(0);
    },
    onError: (err) => {
      setVideoStatus(err instanceof Error ? err.message : "Video generation failed");
    }
  });

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
    const storageKey = storyId ? `lastSceneId:${storyId}` : "";
    const storedSceneId = storageKey ? window.localStorage.getItem(storageKey) : null;
    if (!selectedSceneId) {
      if (storedSceneId && scenesQuery.data.some((scene) => scene.scene_id === storedSceneId)) {
        setSelectedSceneId(storedSceneId);
      } else {
        setSelectedSceneId(scenesQuery.data[0].scene_id);
      }
    }
  }, [scenesQuery.data, selectedSceneId]);

  useEffect(() => {
    if (!storyId || !selectedSceneId) return;
    window.localStorage.setItem(`lastSceneId:${storyId}`, selectedSceneId);
  }, [storyId, selectedSceneId]);

  useEffect(() => {
    const row = scenesRowRef.current;
    if (!row || !selectedSceneId) return;
    const card = sceneCardRefs.current[selectedSceneId];
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [selectedSceneId]);

  useEffect(() => {
    const row = scenesRowRef.current;
    if (!row) return;
    const updateOverflow = () => {
      setScenesOverflow(row.scrollWidth > row.clientWidth + 4);
    };
    updateOverflow();
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(updateOverflow);
      observer.observe(row);
    }
    window.addEventListener("resize", updateOverflow);
    return () => {
      window.removeEventListener("resize", updateOverflow);
      if (observer) observer.disconnect();
    };
  }, [scenesQuery.data?.length]);

  const selectedScene = useMemo(
    () => scenesQuery.data?.find((scene) => scene.scene_id === selectedSceneId),
    [scenesQuery.data, selectedSceneId]
  );

  useEffect(() => {
    if (dialogueLayerQuery.data?.bubbles) {
      const loaded: DialogueBubble[] = dialogueLayerQuery.data.bubbles.map((bubble: any) => ({
        id: bubble.bubble_id,
        panelId: bubble.panel_id,
        text: bubble.text,
        position: bubble.position,
        size: bubble.size,
        tail: bubble.tail ?? null
      }));
      setBubbles(loaded);
      setActiveBubbleId(loaded[0]?.id ?? null);
    } else {
      setBubbles([]);
      setActiveBubbleId(null);
    }
  }, [dialogueLayerQuery.data, selectedSceneId]);

  useEffect(() => {
    if (!lastExportId) return;
    let active = true;
    setPollSeconds(0);
    const interval = setInterval(async () => {
      try {
        const job = await fetchExport(lastExportId);
        if (!active) return;
        setVideoStatus(job.status);
        const errorMessage =
          typeof job?.metadata_?.error === "string" ? job.metadata_.error : null;
        setVideoError(errorMessage);
        if (job.status === "succeeded" && job.output_url) {
          setVideoUrl(`http://localhost:8000${job.output_url}`);
          if (!autoOpened) {
            setAutoOpened(true);
          }
          clearInterval(interval);
        }
        if (job.status === "failed") {
          clearInterval(interval);
        }
        setPollSeconds((prev) => prev + 2);
      } catch {
        clearInterval(interval);
      }
    }, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [lastExportId]);

  if (!storyId) {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink">Dialogue Editor</h1>
          <p className="mt-2 text-slate-500">Select a project and story to edit dialogue.</p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-ink">Project</label>
              <select
                className="input w-full"
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value);
                  setStoryId("");
                  setSelectedSceneId("");
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
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-6xl space-y-4 px-4 sm:px-6">
      <div className="surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-ink">Dialogue Editor</h2>
            <p className="mt-1 text-xs text-slate-500">
              Select a scene and place dialogue bubbles on the render.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              className="input text-sm"
              value={projectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                setStoryId("");
                setSelectedSceneId("");
              }}
            >
              <option value="">Select project</option>
              {projectsQuery.data?.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
            <select
              className="input text-sm"
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
      </div>

      <div className="surface px-4 py-2">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Scenes</h3>
          <div className="flex items-center gap-2">
            {scenesQuery.isLoading && <p className="text-xs text-slate-400">Loading…</p>}
            <button
              className="btn-ghost text-xs"
              onClick={() => scenesRowRef.current?.scrollBy({ left: -280, behavior: "smooth" })}
              disabled={!scenesOverflow}
              aria-label="Scroll scenes left"
            >
              ◀
            </button>
            <button
              className="btn-ghost text-xs"
              onClick={() => scenesRowRef.current?.scrollBy({ left: 280, behavior: "smooth" })}
              disabled={!scenesOverflow}
              aria-label="Scroll scenes right"
            >
              ▶
            </button>
          </div>
        </div>
        <div
          ref={scenesRowRef}
          className="mt-2 flex gap-3 overflow-x-auto pb-2 flex-nowrap"
          onWheel={(event) => {
            const row = scenesRowRef.current;
            if (!row || !scenesOverflow) return;
            if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
              event.preventDefault();
              row.scrollLeft += event.deltaY;
            }
          }}
        >
          {scenesQuery.data?.length === 0 && (
            <div className="text-sm text-slate-500">
              No scenes found. Generate scenes first in Scene Editor.
            </div>
          )}
          {scenesQuery.data?.map((scene, index) => (
            <button
              key={scene.scene_id}
              className={`min-w-[220px] text-left rounded-xl border px-3 py-2 transition ${
                scene.scene_id === selectedSceneId
                  ? "border-indigo-400 bg-indigo-50"
                  : "border-slate-200 bg-white/70 hover:border-indigo-200"
              }`}
              ref={(node) => {
                sceneCardRefs.current[scene.scene_id] = node;
              }}
              onClick={() => setSelectedSceneId(scene.scene_id)}
            >
              <p className="text-sm font-semibold text-ink">Scene {index + 1}</p>
              <p className="mt-1 text-xs text-slate-500 line-clamp-2">
                {scene.source_text}
              </p>
            </button>
          ))}
        </div>
      </div>

      <section className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)_360px] xl:grid-cols-[280px_minmax(0,1fr)_400px] items-stretch min-h-[calc(100vh-340px)]">
        <div className="surface p-5 h-full flex flex-col gap-5 min-w-0">
          <div>
            <h3 className="text-lg font-semibold text-ink">Tools</h3>
            <p className="mt-1 text-xs text-slate-500">
              Drag dialogue lines from this panel onto the canvas.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {([
              { id: "select", label: "Select" },
              { id: "speech", label: "Speech Bubble" },
              { id: "tail", label: "Tail" },
              { id: "delete", label: "Delete" }
            ] as const).map((tool) => (
              <button
                key={tool.id}
                className={`btn-ghost text-xs ${
                  activeTool === tool.id ? "border border-indigo-300 text-indigo-600" : ""
                }`}
                title={`Use the ${tool.label} tool on the canvas.`}
                onClick={() => setActiveTool(tool.id)}
              >
                {tool.label}
              </button>
            ))}
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Inspector</p>
            <div className="mt-3 space-y-2">
              <select className="input text-xs">
                <option>Speech</option>
                <option>Thought</option>
                <option>Narration</option>
                <option>SFX</option>
              </select>
              <input
                className="input"
                placeholder="Speaker"
                value={
                  bubbles.find((bubble) => bubble.id === activeBubbleId)?.speaker ?? ""
                }
                onChange={(e) => {
                  const value = e.target.value;
                  setBubbles((prev) =>
                    prev.map((bubble) =>
                      bubble.id === activeBubbleId ? { ...bubble, speaker: value } : bubble
                    )
                  );
                }}
                disabled={!activeBubbleId}
              />
              <textarea
                className="textarea"
                placeholder="Dialogue text"
                value={
                  bubbles.find((bubble) => bubble.id === activeBubbleId)?.text ?? ""
                }
                onChange={(e) => {
                  const value = e.target.value;
                  setBubbles((prev) =>
                    prev.map((bubble) =>
                      bubble.id === activeBubbleId
                        ? {
                            ...bubble,
                            text: value,
                            size: {
                              ...bubble.size,
                              h: estimateBubbleHeight(value, bubble.size.w)
                            }
                          }
                        : bubble
                    )
                  );
                }}
                disabled={!activeBubbleId}
              />
            </div>
          </div>
          <div className="flex-1" />
          <button
            className="btn-primary text-xs"
            title="Save dialogue bubbles for this scene."
            onClick={() => {
              setSaveError(null);
              saveLayerMutation.mutate();
            }}
            disabled={!selectedSceneId || saveLayerMutation.isPending}
          >
            {saveLayerMutation.isPending ? "Saving..." : "Save Layer"}
          </button>
          {saveLayerMutation.isError && (
            <p className="text-xs text-rose-500">
              {saveError || "Unable to save dialogue layer."}
            </p>
          )}
        </div>

        <div className="surface p-5 flex flex-col gap-4 min-h-[calc(100vh-340px)] min-w-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-ink">Dialogue Canvas</h2>
            <div className="flex items-center gap-2">
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
              <button className="btn-ghost text-xs" onClick={() => setZoom(1)}>
                Fit
              </button>
            </div>
          </div>
          <div className="flex-1 flex items-center justify-center min-h-[520px]">
            {selectedScene ? (
              <SceneCanvas
                scene={selectedScene}
                bubbles={bubbles}
                onBubbleSelect={(bubbleId) => setActiveBubbleId(bubbleId)}
                onBubbleChange={(updated) => {
                  setBubbles((prev) =>
                    prev.map((bubble) => (bubble.id === updated.id ? updated : bubble))
                  );
                }}
                onBubbleAdd={(bubble) => {
                  setBubbles((prev) => [...prev, bubble]);
                  setActiveBubbleId(bubble.id);
                }}
                onBubbleDelete={(bubbleId) => {
                  setBubbles((prev) => prev.filter((bubble) => bubble.id !== bubbleId));
                  setActiveBubbleId((current) => (current === bubbleId ? null : current));
                }}
                activeTool={activeTool}
                zoom={zoom}
              />
            ) : (
              <div className="relative aspect-[9/16] w-full max-w-md rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft">
                <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
                  Select a scene to load the canvas.
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="surface p-5 h-full flex flex-col gap-5 min-w-0">
          <div>
            <h4 className="text-sm font-semibold text-ink">Dialogue Lines</h4>
            <div className="mt-3 space-y-4 flex-1 overflow-auto">
              {selectedScene ? (
                <SceneDialogueList sceneId={selectedScene.scene_id} />
              ) : (
                <div className="card text-sm text-slate-500">
                  Select a scene to view dialogue.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-semibold text-ink">Generate Video</h4>
            <p className="mt-1 text-xs text-slate-500">
              Create an episode export and generate a vertical video.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="input text-xs"
              value={selectedEpisodeId}
              onChange={(e) => setSelectedEpisodeId(e.target.value)}
              disabled={!storyId}
            >
              <option value="">Select episode</option>
              {episodesQuery.data?.map((episode: any) => (
                <option key={episode.episode_id} value={episode.episode_id}>
                  {episode.title}
                </option>
              ))}
            </select>
            {episodesQuery.data?.length === 0 && storyQuery.data && (
              <button
                className="btn-ghost text-xs"
                onClick={() => createEpisodeMutation.mutate()}
                disabled={createEpisodeMutation.isPending}
              >
                {createEpisodeMutation.isPending ? "Creating..." : "Create Episode"}
              </button>
            )}
            <button
              className="btn-primary text-xs"
              onClick={() => {
                setVideoStatus(null);
                setVideoUrl(null);
                setVideoError(null);
                setPollSeconds(0);
                generateVideoMutation.mutate();
              }}
              disabled={!selectedEpisodeId || generateVideoMutation.isPending}
            >
              {generateVideoMutation.isPending ? "Generating..." : "Generate Video"}
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
          {videoStatus && (
            <div className="flex items-center gap-2">
              {videoStatus === "processing" && (
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-500" />
              )}
              <span>Status: {videoStatus}</span>
              {videoStatus === "processing" && <span>({pollSeconds}s)</span>}
            </div>
          )}
          {lastExportId && (
            <p className="text-[11px] text-slate-400">Export ID: {lastExportId.slice(0, 8)}…</p>
          )}
          {videoError && <p className="text-xs text-rose-500">Error: {videoError}</p>}
          {videoUrl && (
            <div className="flex items-center gap-2">
              <a
                className="text-xs text-indigo-500 hover:text-indigo-600"
                href={videoUrl}
                target="_blank"
                rel="noreferrer"
                download
              >
                Download video
              </a>
              <button
                className="btn-ghost text-[11px]"
                onClick={() => window.open(videoUrl, "_blank", "noopener")}
              >
                Open
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

type DialogueBubble = {
  id: string;
  panelId: number;
  text: string;
  speaker?: string;
  position: { x: number; y: number };
  size: { w: number; h: number };
  tail?: { x: number; y: number } | null;
};

function estimateBubbleHeight(text: string, widthRatio: number) {
  const normalized = text.trim();
  if (!normalized) return 0.08;
  const charsPerLine = Math.max(12, Math.floor(widthRatio * 70));
  const rawLines = normalized.split("\n");
  const lines = rawLines.reduce((count, line) => {
    const len = Math.max(1, line.length);
    return count + Math.ceil(len / charsPerLine);
  }, 0);
  const base = 0.05;
  const perLine = 0.03;
  return Math.min(0.55, Math.max(base + lines * perLine, 0.08));
}

function SceneCanvas({
  scene,
  bubbles,
  onBubbleSelect,
  onBubbleChange,
  onBubbleAdd,
  onBubbleDelete,
  activeTool,
  zoom
}: {
  scene: Scene;
  bubbles: DialogueBubble[];
  onBubbleSelect: (bubbleId: string) => void;
  onBubbleChange: (bubble: DialogueBubble) => void;
  onBubbleAdd: (bubble: DialogueBubble) => void;
  onBubbleDelete: (bubbleId: string) => void;
  activeTool: "select" | "speech" | "tail" | "delete";
  zoom: number;
}) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [dragGhost, setDragGhost] = useState<{ x: number; y: number } | null>(null);
  const [draggingBubbleId, setDraggingBubbleId] = useState<string | null>(null);
  const [resizingBubbleId, setResizingBubbleId] = useState<string | null>(null);
  const [tailDraggingId, setTailDraggingId] = useState<string | null>(null);
  const dragOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    if (!draggingBubbleId && !resizingBubbleId && !tailDraggingId) return;
    const handleMove = (event: PointerEvent) => {
      if (!canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      if (draggingBubbleId) {
        const x = (event.clientX - rect.left - dragOffsetRef.current.x) / rect.width;
        const y = (event.clientY - rect.top - dragOffsetRef.current.y) / rect.height;
        const clampedX = Math.max(0.02, Math.min(0.98, x));
        const clampedY = Math.max(0.02, Math.min(0.98, y));
        const bubble = bubbles.find((item) => item.id === draggingBubbleId);
        if (!bubble) return;
        onBubbleChange({
          ...bubble,
          position: { x: clampedX, y: clampedY }
        });
      }

      if (resizingBubbleId) {
        const bubble = bubbles.find((item) => item.id === resizingBubbleId);
        if (!bubble) return;
        const bubbleCenterX = bubble.position.x * rect.width;
        const width = Math.abs(event.clientX - rect.left - bubbleCenterX) * 2;
        const nextW = Math.max(0.12, Math.min(0.9, width / rect.width));
        const autoH = estimateBubbleHeight(bubble.text, nextW);
        onBubbleChange({
          ...bubble,
          size: { w: nextW, h: autoH }
        });
      }

      if (tailDraggingId) {
        const bubble = bubbles.find((item) => item.id === tailDraggingId);
        if (!bubble) return;
        const tailX = (event.clientX - rect.left) / rect.width;
        const tailY = (event.clientY - rect.top) / rect.height;
        onBubbleChange({
          ...bubble,
          tail: {
            x: Math.max(0.02, Math.min(0.98, tailX)),
            y: Math.max(0.02, Math.min(0.98, tailY))
          }
        });
      }
    };

    const handleUp = () => {
      setDraggingBubbleId(null);
      setResizingBubbleId(null);
      setTailDraggingId(null);
    };

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
  }, [bubbles, draggingBubbleId, resizingBubbleId, tailDraggingId, onBubbleChange]);
  const rendersQuery = useQuery({
    queryKey: ["renders", scene.scene_id],
    queryFn: () => fetchSceneRenders(scene.scene_id)
  });

  const latestRender = rendersQuery.data
    ? getLatestArtifact(rendersQuery.data, "render_result")
    : null;

  const imageUrl = latestRender?.payload?.image_url
    ? getImageUrl(String(latestRender.payload.image_url))
    : null;

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = 0;
    }
  }, [scene.scene_id]);

  return (
    <div
      ref={viewportRef}
      className="relative h-full w-full max-w-none overflow-auto rounded-2xl bg-slate-100 shadow-soft"
    >
      <div
        ref={canvasRef}
        className="relative aspect-[9/16] w-full max-w-[680px] rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft overflow-hidden"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const raw = event.dataTransfer.getData("application/x-dialogue");
          if (!raw || !canvasRef.current) return;
          const data = JSON.parse(raw) as { text: string; speaker?: string };
          const rect = canvasRef.current.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width;
          const y = (event.clientY - rect.top) / rect.height;
          const clampedX = Math.max(0.02, Math.min(0.92, x));
          const clampedY = Math.max(0.02, Math.min(0.92, y));
          onBubbleAdd({
            id: crypto.randomUUID(),
            panelId: 1,
            text: data.text,
            speaker: data.speaker,
            position: { x: clampedX, y: clampedY },
            size: { w: 0.28, h: estimateBubbleHeight(data.text, 0.28) }
          });
          setDragGhost(null);
        }}
        onDragEnter={(event) => {
          if (!canvasRef.current) return;
          const rect = canvasRef.current.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width;
          const y = (event.clientY - rect.top) / rect.height;
          setDragGhost({ x, y });
        }}
        onDragLeave={() => setDragGhost(null)}
        onDragOverCapture={(event) => {
          if (!canvasRef.current) return;
          const rect = canvasRef.current.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width;
          const y = (event.clientY - rect.top) / rect.height;
          setDragGhost({ x, y });
        }}
        onClick={(event) => {
          if (activeTool !== "speech") return;
          if (!canvasRef.current) return;
          const target = event.target as HTMLElement;
          if (target.closest("[data-bubble='true']")) return;
          const rect = canvasRef.current.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width;
          const y = (event.clientY - rect.top) / rect.height;
          const clampedX = Math.max(0.02, Math.min(0.92, x));
          const clampedY = Math.max(0.02, Math.min(0.92, y));
          onBubbleAdd({
            id: crypto.randomUUID(),
            panelId: 1,
            text: "New dialogue",
            position: { x: clampedX, y: clampedY },
            size: { w: 0.28, h: estimateBubbleHeight("New dialogue", 0.28) }
          });
        }}
        style={{ transform: `scale(${zoom})`, transformOrigin: "top center" }}
      >
        {imageUrl ? (
          <img src={imageUrl} alt="Scene render" className="h-full w-full object-contain" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
            {rendersQuery.isLoading ? "Loading render..." : "No render found for this scene."}
          </div>
        )}
        {bubbles.map((bubble) => (
          <div key={bubble.id}>
            <button
              type="button"
              className="absolute rounded-xl bg-white/90 text-[11px] text-slate-700 shadow-soft px-2 py-0.5 border border-slate-200 hover:border-indigo-300"
              style={{
                left: `${bubble.position.x * 100}%`,
                top: `${bubble.position.y * 100}%`,
                width: `${bubble.size.w * 100}%`,
                height: `${bubble.size.h * 100}%`,
                minWidth: "80px",
                transform: "translate(-50%, -50%)"
              }}
              onClick={() => {
                if (activeTool === "delete") {
                  onBubbleDelete(bubble.id);
                  return;
                }
                onBubbleSelect(bubble.id);
              }}
              onPointerDown={(event) => {
                if (activeTool !== "select") return;
                if (!canvasRef.current) return;
                const rect = canvasRef.current.getBoundingClientRect();
                const bubbleX = bubble.position.x * rect.width;
                const bubbleY = bubble.position.y * rect.height;
                dragOffsetRef.current = {
                  x: event.clientX - rect.left - bubbleX,
                  y: event.clientY - rect.top - bubbleY
                };
                setDraggingBubbleId(bubble.id);
              }}
              data-bubble="true"
            >
              <span className="block whitespace-pre-wrap break-words leading-snug">
                {bubble.text}
              </span>
            </button>
            {activeTool === "select" && (
              <button
                type="button"
                className="absolute h-3 w-3 rounded-full border border-indigo-300 bg-white shadow"
                style={{
                  left: `${(bubble.position.x + bubble.size.w / 2) * 100}%`,
                  top: `${(bubble.position.y + bubble.size.h / 2) * 100}%`,
                  transform: "translate(-50%, -50%)"
                }}
                onPointerDown={(event) => {
                  event.stopPropagation();
                  setResizingBubbleId(bubble.id);
                }}
                data-bubble="true"
              />
            )}
            {activeTool === "tail" && (
              <button
                type="button"
                className="absolute h-3 w-3 rounded-full border border-indigo-300 bg-indigo-100 shadow"
                style={{
                  left: `${(bubble.tail?.x ?? bubble.position.x) * 100}%`,
                  top: `${(bubble.tail?.y ?? bubble.position.y + bubble.size.h / 2) * 100}%`,
                  transform: "translate(-50%, -50%)"
                }}
                onPointerDown={(event) => {
                  event.stopPropagation();
                  onBubbleSelect(bubble.id);
                  setTailDraggingId(bubble.id);
                }}
                data-bubble="true"
              />
            )}
          </div>
        ))}
        {dragGhost && (
          <div
            className="absolute rounded-xl border border-dashed border-indigo-300 bg-white/60 text-[11px] text-indigo-400 px-2 py-1 pointer-events-none"
            style={{
              left: `${Math.max(0.02, Math.min(0.92, dragGhost.x)) * 100}%`,
              top: `${Math.max(0.02, Math.min(0.92, dragGhost.y)) * 100}%`,
              width: "28%",
              minWidth: "80px",
              transform: "translate(-50%, -50%)"
            }}
          >
            Drop here
          </div>
        )}
      </div>
    </div>
  );
}

function SceneDialogueList({ sceneId }: { sceneId: string }) {
  const suggestionsQuery = useQuery({
    queryKey: ["dialogue-suggestions", sceneId],
    queryFn: () => fetchDialogueSuggestions(sceneId),
    enabled: sceneId.length > 0
  });

  if (suggestionsQuery.isLoading) {
    return <div className="card text-sm text-slate-500">Loading dialogue suggestions...</div>;
  }

  if (suggestionsQuery.isError) {
    return (
      <div className="card text-sm text-slate-500">
        Dialogue suggestions not available yet.
      </div>
    );
  }

  const suggestions: DialogueSuggestion[] = suggestionsQuery.data?.suggestions ?? [];

  if (suggestions.length === 0) {
    return <div className="card text-sm text-slate-500">No dialogue lines found.</div>;
  }

  return (
    <div className="space-y-3">
      {suggestions.map((line, idx) => (
        <div
          key={`${line.speaker}-${idx}`}
          className="card text-xs text-slate-600 cursor-grab active:cursor-grabbing"
          draggable
          onDragStart={(event) => {
            event.dataTransfer.setData(
              "application/x-dialogue",
              JSON.stringify({ text: line.text, speaker: line.speaker })
            );
            event.dataTransfer.effectAllowed = "copy";
          }}
        >
          <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Panel {line.panel_hint ?? idx + 1}
          </p>
          <p className="mt-2 font-semibold text-ink">{line.speaker}</p>
          <p className="mt-1 text-slate-600">{line.text}</p>
          <p className="mt-2 text-[11px] text-slate-400">Emotion: {line.emotion}</p>
          <p className="mt-2 text-[11px] text-slate-400">
            Drag this line onto the canvas.
          </p>
        </div>
      ))}
    </div>
  );
}
