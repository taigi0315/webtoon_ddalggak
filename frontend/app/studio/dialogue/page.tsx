"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchStories,
  fetchScenes,
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
import type { Scene } from "@/lib/api/types";
import { getImageUrl } from "@/lib/utils/media";
import {
  SceneCanvas,
  SceneDialogueList,
  estimateBubbleHeight,
  type DialogueBubble,
  type ToolType
} from "@/components/studio/dialogue";

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

      // Allow saving with zero bubbles - dialogue is optional
      const payloadBubbles = validBubbles.map((bubble) => ({
        bubble_id: bubble.id,
        panel_id: bubble.panelId,
        bubble_type: bubble.bubbleType ?? "chat",
        speaker: bubble.speaker ?? null,
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
        defaultImageStyle: storyQuery.data.default_image_style
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["episodes", storyId] });
    }
  });

  const generateVideoMutation = useMutation({
    mutationFn: async () => {
      if (!scenesQuery.data || scenesQuery.data.length === 0) {
        throw new Error("No scenes found for this story");
      }

      // Auto-create or find episode with story name
      let episodeId = selectedEpisodeId;

      if (!episodeId) {
        // Check if episode with story name exists
        const existingEpisode = episodesQuery.data?.find(
          (ep) => ep.title === storyQuery.data?.title
        );

        if (existingEpisode) {
          episodeId = existingEpisode.episode_id;
          setSelectedEpisodeId(episodeId);
        } else {
          // Auto-create episode with story name
          if (!storyQuery.data) throw new Error("Story not found");
          const newEpisode = await createEpisode({
            storyId,
            title: storyQuery.data.title,
            defaultImageStyle: storyQuery.data.default_image_style
          });
          episodeId = newEpisode.episode_id;
          setSelectedEpisodeId(episodeId);
          await queryClient.invalidateQueries({ queryKey: ["episodes", storyId] });
        }
      }

      const selectedEpisode = episodesQuery.data?.find(
        (episode) => episode.episode_id === episodeId
      );
      const episodeSceneIds = selectedEpisode?.scene_ids_ordered ?? [];
      const sceneIds =
        episodeSceneIds.length > 0
          ? episodeSceneIds
          : scenesQuery.data.map((scene) => scene.scene_id);
      if (episodeSceneIds.length === 0) {
        await setEpisodeScenes({ episodeId, sceneIds });
        await queryClient.invalidateQueries({ queryKey: ["episodes", storyId] });
      }
      const exportJob = await createEpisodeExport(episodeId);
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
        bubbleType: bubble.bubble_type ?? "chat",
        speaker: bubble.speaker ?? undefined,
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
          setVideoUrl(getImageUrl(job.output_url));
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
              className={`min-w-[220px] text-left rounded-xl border px-3 py-2 transition ${scene.scene_id === selectedSceneId
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
                className={`btn-ghost text-xs ${activeTool === tool.id ? "border border-indigo-300 text-indigo-600" : ""
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
              <select
                className="input text-xs"
                value={
                  bubbles.find((bubble) => bubble.id === activeBubbleId)?.bubbleType ?? "chat"
                }
                onChange={(e) => {
                  const value = e.target.value;
                  setBubbles((prev) =>
                    prev.map((bubble) =>
                      bubble.id === activeBubbleId ? { ...bubble, bubbleType: value } : bubble
                    )
                  );
                }}
                disabled={!activeBubbleId}
              >
                <option value="chat">Dialogue</option>
                <option value="thought">Thought</option>
                <option value="narration">Narration</option>
                <option value="sfx">SFX</option>
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
            <button
              className="btn-primary text-xs"
              onClick={() => {
                setVideoStatus(null);
                setVideoUrl(null);
                setVideoError(null);
                setPollSeconds(0);
                generateVideoMutation.mutate();
              }}
              disabled={!storyId || generateVideoMutation.isPending || !scenesQuery.data || scenesQuery.data.length === 0}
            >
              {generateVideoMutation.isPending ? "Generating..." : "Generate Video"}
            </button>
            {(!scenesQuery.data || scenesQuery.data.length === 0) && (
              <span className="text-xs text-slate-400">Add scenes to enable video generation</span>
            )}
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

