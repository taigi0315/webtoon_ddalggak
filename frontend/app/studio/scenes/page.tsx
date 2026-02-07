"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProjects,
  fetchStories,
  fetchStory,
  fetchScenes,
  fetchSceneStatus,
  fetchSceneArtifacts,
  fetchSceneRenders,
  planSceneAsync,
  generateSceneRenderAsync,
  fetchJob
} from "@/lib/api/queries";
import type { Scene } from "@/lib/api/types";
import { getLatestArtifact } from "@/lib/utils/artifacts";
import { getImageUrl } from "@/lib/utils/media";

export default function ScenesPage() {
  const [projectId, setProjectId] = useState("");
  const [storyId, setStoryId] = useState("");
  const [selectedSceneId, setSelectedSceneId] = useState("");
  const [promptOverride, setPromptOverride] = useState<string | null>(null);
  const [isGeneratingAll, setIsGeneratingAll] = useState(false);
  const [activeJobs, setActiveJobs] = useState<Record<string, string>>({});
  const [planningJobs, setPlanningJobs] = useState<Record<string, string>>({});
  const [planningStatusByScene, setPlanningStatusByScene] = useState<Record<string, boolean>>({});
  const plannedSceneIdsRef = useRef<Set<string>>(new Set());
  const queryClient = useQueryClient();

  // Global polling for active jobs
  useEffect(() => {
    const renderEntries = Object.entries(activeJobs).map(([sceneId, jobId]) => ({
      sceneId,
      jobId,
      kind: "render" as const
    }));
    const planEntries = Object.entries(planningJobs).map(([sceneId, jobId]) => ({
      sceneId,
      jobId,
      kind: "plan" as const
    }));
    const entries = [...renderEntries, ...planEntries];
    if (entries.length === 0) return;

    const interval = setInterval(async () => {
      let updatedRenderJobs = { ...activeJobs };
      let updatedPlanJobs = { ...planningJobs };
      let changed = false;

      await Promise.all(
        entries.map(async ({ sceneId, jobId, kind }) => {
          try {
            const status = await fetchJob(jobId);
            if (["completed", "succeeded", "failed", "cancelled"].includes(status.status)) {
              if (kind === "render") {
                delete updatedRenderJobs[sceneId];
              } else {
                delete updatedPlanJobs[sceneId];
              }
              changed = true;

              if (status.status === "failed" && status.error) {
                console.error(`${kind} job failed for ${sceneId}:`, status.error);
                alert(`Scene ${kind} failed: ${status.error}`);
              }

              queryClient.invalidateQueries({ queryKey: ["artifacts", sceneId] });
              if (kind === "render") {
                queryClient.invalidateQueries({ queryKey: ["renders", sceneId] });
              } else {
                setPlanningStatusByScene((prev) => ({ ...prev, [sceneId]: status.status !== "failed" }));
              }
            }
          } catch (e) {
            console.error(`Failed to poll job ${jobId}`, e);
          }
        })
      );

      if (changed) {
        setActiveJobs(updatedRenderJobs);
        setPlanningJobs(updatedPlanJobs);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeJobs, planningJobs, queryClient]);

  const handleJobStarted = (sceneId: string, jobId: string) => {
    setActiveJobs((prev) => ({ ...prev, [sceneId]: jobId }));
  };

  const handlePlanJobStarted = (sceneId: string, jobId: string) => {
    setPlanningJobs((prev) => ({ ...prev, [sceneId]: jobId }));
  };

  const handleGenerateAll = async () => {
    if (!storyId || !scenesQuery.data) return;
    if (!confirm("This will regenerate images for ALL scenes in the story. Continue?")) return;
    setIsGeneratingAll(true);

    const styleId = storyQuery.data?.default_image_style ?? "default";

    try {
      const promises = scenesQuery.data.map(async (scene) => {
        try {
          const res = await generateSceneRenderAsync({
            sceneId: scene.scene_id,
            styleId: scene.image_style_override ?? styleId
          });
          handleJobStarted(scene.scene_id, res.job_id);
        } catch (e) {
          console.error(`Failed to start job for scene ${scene.scene_id}`, e);
        }
      });

      await Promise.all(promises);
      alert(`Started generation for ${scenesQuery.data.length} scenes.`);
    } catch (err) {
      alert("Failed to start batch generation: " + (err instanceof Error ? err.message : "Unknown error"));
    } finally {
      setIsGeneratingAll(false);
    }
  };

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
    plannedSceneIdsRef.current = new Set();
    setPlanningJobs({});
    setPlanningStatusByScene({});
  }, [storyId]);

  useEffect(() => {
    if (!storyId || !scenesQuery.data || scenesQuery.data.length === 0) return;
    let cancelled = false;

    const runPlanning = async () => {
      for (const scene of scenesQuery.data) {
        if (cancelled) return;
        if (planningJobs[scene.scene_id]) continue;
        if (plannedSceneIdsRef.current.has(scene.scene_id)) continue;

        try {
          const status = await fetchSceneStatus(scene.scene_id);
          if (cancelled) return;
          plannedSceneIdsRef.current.add(scene.scene_id);
          setPlanningStatusByScene((prev) => ({
            ...prev,
            [scene.scene_id]: status.planning_complete
          }));

          if (!status.planning_complete) {
            const job = await planSceneAsync({ sceneId: scene.scene_id, panelCount: 3 });
            if (cancelled) return;
            handlePlanJobStarted(scene.scene_id, job.job_id);
          }
        } catch (e) {
          console.error(`Failed to check planning status for ${scene.scene_id}`, e);
        }
      }
    };

    runPlanning();
    return () => {
      cancelled = true;
    };
  }, [storyId, scenesQuery.data, planningJobs]);

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

  const selectedScene = useMemo(
    () => scenesQuery.data?.find((scene) => scene.scene_id === selectedSceneId),
    [scenesQuery.data, selectedSceneId]
  );

  const planningSummary = useMemo(() => {
    const total = scenesQuery.data?.length ?? 0;
    if (total === 0) {
      return { total: 0, done: 0, inProgress: false };
    }
    const done = scenesQuery.data?.filter((scene) => planningStatusByScene[scene.scene_id]).length ?? 0;
    const inProgress = Object.keys(planningJobs).length > 0;
    return { total, done, inProgress };
  }, [scenesQuery.data, planningStatusByScene, planningJobs]);

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
            <button
              className="btn-secondary text-sm"
              onClick={handleGenerateAll}
              disabled={isGeneratingAll || !storyId}
            >
              {isGeneratingAll ? "Queuing..." : "Generate All"}
            </button>
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[260px,1fr,320px]">
          <aside className="flex flex-col gap-2">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Scenes</p>
            {planningSummary.total > 0 && (planningSummary.inProgress || planningSummary.done < planningSummary.total) && (
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-[11px] text-indigo-700">
                Planning scenes: {planningSummary.done}/{planningSummary.total}
                {planningSummary.inProgress ? " (in progress)" : ""}
              </div>
            )}
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
                className={`w-full text-left rounded-lg border px-3 py-2 transition ${scene.scene_id === selectedSceneId
                  ? "border-indigo-400 bg-indigo-50"
                  : "border-slate-200 bg-white/70 hover:border-indigo-200"
                  }`}
                onClick={() => setSelectedSceneId(scene.scene_id)}
              >
                <p className="text-sm font-semibold text-ink">Scene {index + 1}</p>
                <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">
                  {scene.source_text}
                </p>
                {planningJobs[scene.scene_id] && (
                  <p className="mt-1 text-[11px] text-indigo-500">Planning...</p>
                )}
                {!planningJobs[scene.scene_id] &&
                  planningStatusByScene[scene.scene_id] === false && (
                    <p className="mt-1 text-[11px] text-amber-600">Planning queued</p>
                  )}
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
                imageStyle={storyQuery.data?.default_image_style}
                promptOverride={promptOverride}
                activeJobId={activeJobs[selectedScene.scene_id]}
                planningJobId={planningJobs[selectedScene.scene_id]}
                onJobStarted={handleJobStarted}
                onPlanJobStarted={handlePlanJobStarted}
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
            <ProceedToDialogueButton
              scenes={scenesQuery.data}
              activeJobs={activeJobs}
              isGeneratingAll={isGeneratingAll}
            />
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
  imageStyle,
  promptOverride,
  activeJobId,
  planningJobId,
  onJobStarted,
  onPlanJobStarted
}: {
  scene: Scene;
  imageStyle?: string;
  promptOverride?: string | null;
  activeJobId?: string;
  planningJobId?: string;
  onJobStarted: (sceneId: string, jobId: string) => void;
  onPlanJobStarted: (sceneId: string, jobId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");
  const [imageLoadError, setImageLoadError] = useState("");

  // Derived state from prop
  const isGenerating = !!activeJobId;
  const isPlanning = !!planningJobId;

  const [zoom, setZoom] = useState(1);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [selectedPromptVersion, setSelectedPromptVersion] = useState<number | null>(null);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

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

  // Polling for job status
  // Polling is now handled by parent via activeJobId
  useEffect(() => {
    // Reset transient errors when scene changes
    setError("");
    setImageLoadError("");
    setIsStarting(false);
  }, [scene.scene_id]);

  const renderMutation = useMutation({
    mutationFn: generateSceneRenderAsync,
    onSuccess: (data) => {
      onJobStarted(scene.scene_id, data.job_id);
      setIsStarting(false);
      setError("");
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Generation failed");
      setIsStarting(false);
    }
  });

  const planMutation = useMutation({
    mutationFn: planSceneAsync,
    onSuccess: (data) => {
      onPlanJobStarted(scene.scene_id, data.job_id);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Planning failed");
    }
  });

  const latestRenderFromRenders = rendersQuery.data
    ? getLatestArtifact(rendersQuery.data, "render_result")
    : null;
  const latestRenderFromArtifacts = artifactsQuery.data
    ? getLatestArtifact(artifactsQuery.data, "render_result")
    : null;
  const latestRender = latestRenderFromRenders ?? latestRenderFromArtifacts;

  const currentRender = useMemo(() => {
    if (selectedArtifactId && rendersQuery.data) {
      const found = rendersQuery.data.find((r) => r.artifact_id === selectedArtifactId);
      if (found) return found;
    }
    return latestRender;
  }, [rendersQuery.data, selectedArtifactId, latestRender]);

  const hasSemantics = artifactsQuery.data
    ? !!getLatestArtifact(artifactsQuery.data, "panel_semantics")
    : false;
  const hasLayout = artifactsQuery.data
    ? !!getLatestArtifact(artifactsQuery.data, "layout_template")
    : false;
  const planningComplete = hasSemantics && hasLayout;
  const qcReport = artifactsQuery.data
    ? getLatestArtifact(artifactsQuery.data, "qc_report")
    : null;
  const qcPayload =
    qcReport && qcReport.payload && typeof qcReport.payload === "object"
      ? (qcReport.payload as Record<string, any>)
      : null;
  const qcFailed = qcPayload?.passed === false;
  const qcIssueDetails = Array.isArray(qcPayload?.issue_details)
    ? qcPayload.issue_details
    : [];
  const qcIssues = Array.isArray(qcPayload?.issues) ? qcPayload.issues : [];

  const handleGenerate = async () => {
    setError("");
    if (!planningComplete) {
      setError("Scene planning is not ready yet. Please wait for planning to finish.");
      return;
    }
    setIsStarting(true);
    const normalizedPromptOverride = promptOverride?.trim()
      ? promptOverride.trim()
      : null;
    try {
      await renderMutation.mutateAsync({
        sceneId: scene.scene_id,
        styleId: scene.image_style_override ?? imageStyle ?? "default",
        promptOverride: normalizedPromptOverride,
        enforceQc: false
      });
    } catch {
      // Error handled in mutation
    }
  };

  const handlePlan = async () => {
    setError("");
    try {
      await planMutation.mutateAsync({
        sceneId: scene.scene_id,
        panelCount: 3
      });
    } catch {
      // Error handled in mutation
    }
  };

  // getImageUrl imported from @/lib/utils/media

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

  const rawImageUrl = extractImageUrl(currentRender?.payload);

  const imageUrl = rawImageUrl ? getImageUrl(String(rawImageUrl)) : null;

  useEffect(() => {
    setZoom(1);
    setSelectedPrompt(null);
    setSelectedPromptVersion(null);
    setSelectedArtifactId(null);
  }, [scene.scene_id]);

  // waitingForImage logic removed in favor of isGenerating from prop
  useEffect(() => {
    if (isGenerating && imageUrl) {
      // If we see an image URL but we think we are generating,
      // it means the image is from BEFORE this job started.
      // We keep showing generating state until the job finishes (prop updates).
    }
  }, [isGenerating, imageUrl]);

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-ink">Scene Image</h3>
          <p className="text-xs text-slate-500">
            {planningComplete
              ? "Scene planning ready."
              : isPlanning
                ? "Scene planning in progress."
                : "Scene planning not complete yet."}
          </p>
        </div>
        <button
          className="btn-primary text-sm"
          onClick={handleGenerate}
          disabled={isGenerating || isStarting || isPlanning || !planningComplete}
        >
          {isPlanning
            ? "Planning..."
            : isGenerating || isStarting
              ? "Generating..."
              : !planningComplete
                ? "Waiting for Planning"
                : imageUrl
                  ? "Generate Another"
                  : "Generate Image"}
        </button>
      </div>
      {!planningComplete && !isPlanning && (
        <div className="mt-2">
          <button
            className="btn-ghost text-xs"
            onClick={handlePlan}
            disabled={planMutation.isPending}
          >
            {planMutation.isPending ? "Planning..." : "Retry Planning"}
          </button>
        </div>
      )}

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
            <div className="relative h-[760px] w-full overflow-auto rounded-xl bg-slate-100">
              <img
                src={imageUrl}
                alt="Scene render"
                className="mx-auto rounded-xl object-contain"
                style={{ transform: `scale(${zoom})`, transformOrigin: "top center" }}
                onError={() => setImageLoadError("Unable to load render image.")}
                onLoad={() => {
                  setImageLoadError("");
                }}
              />
            </div>
          ) : (
            <div className="flex h-[520px] w-full items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              {imageLoadError ||
                (isPlanning
                  ? "Planning scene... This can take a minute."
                  : isGenerating
                    ? "Generating image... This can take a minute."
                    : "No scene image yet. Planning runs on entry; generate once ready.")}
            </div>
          )}
        </div>
      </div>

      {qcFailed && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-900">
          <div className="text-sm font-semibold">Quality Warning</div>
          <p className="mt-1 text-xs text-amber-800">
            This render did not pass QC. You can keep it, but consider re-generating
            after adjusting the scene plan or prompt.
          </p>
          {qcPayload?.summary && (
            <p className="mt-1 text-xs text-amber-700">{qcPayload.summary}</p>
          )}
          {(qcIssueDetails.length > 0 || qcIssues.length > 0) && (
            <ul className="mt-2 list-disc pl-4 text-xs text-amber-900">
              {qcIssueDetails.length > 0
                ? qcIssueDetails.map((detail: any, idx: number) => (
                  <li key={`${detail.code || "qc"}-${idx}`}>
                    <span className="font-medium">{detail.message || detail.code}</span>
                    {detail.hint ? (
                      <span className="text-amber-800"> {detail.hint}</span>
                    ) : null}
                  </li>
                ))
                : qcIssues.map((issue: string) => (
                  <li key={issue}>{issue}</li>
                ))}
            </ul>
          )}
        </div>
      )}

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
            {[...rendersQuery.data]
              .sort((a, b) => b.version - a.version)
              .slice(1, 5)
              .map((render) => {
                const url = render.payload?.image_url
                  ? getImageUrl(String(render.payload.image_url))
                  : null;

                if (!url) return null;

                return (
                  <button
                    key={render.artifact_id}
                    className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-slate-200 hover:border-indigo-400"
                    onClick={() => setSelectedArtifactId(render.artifact_id)}
                  >
                    <img
                      src={url}
                      alt={`Version ${render.version}`}
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute bottom-0 right-0 bg-black/50 px-1 text-[10px] text-white">
                      v{render.version}
                    </div>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}

function ProceedToDialogueButton({
  scenes,
  activeJobs,
  isGeneratingAll
}: {
  scenes: Scene[];
  activeJobs: Record<string, string>;
  isGeneratingAll: boolean;
}) {
  // Use useQuery to fetch render data for all scenes
  // This ensures we get real-time updates when renders are generated
  const renderQueries = useQuery({
    queryKey: ["all-scene-renders", scenes.map(s => s.scene_id).join(",")],
    queryFn: async () => {
      const results = await Promise.all(
        scenes.map(async (scene) => {
          try {
            const renders = await fetchSceneRenders(scene.scene_id);
            const artifacts = await fetchSceneArtifacts(scene.scene_id);

            const latestRenderFromRenders = renders
              ? getLatestArtifact(renders, "render_result")
              : null;
            const latestRenderFromArtifacts = artifacts
              ? getLatestArtifact(artifacts, "render_result")
              : null;
            const latestRender = latestRenderFromRenders ?? latestRenderFromArtifacts;

            return {
              sceneId: scene.scene_id,
              hasRender: !!latestRender,
              isGenerating: !!activeJobs[scene.scene_id]
            };
          } catch (error) {
            console.error(`Error checking render for scene ${scene.scene_id}:`, error);
            return {
              sceneId: scene.scene_id,
              hasRender: false,
              isGenerating: !!activeJobs[scene.scene_id]
            };
          }
        })
      );
      return results;
    },
    enabled: scenes.length > 0,
    refetchInterval: 3000, // Refetch every 3 seconds to catch new renders
    staleTime: 2000
  });

  const sceneRenderStatus = renderQueries.data ?? [];
  const allScenesHaveRenders = sceneRenderStatus.length > 0 && sceneRenderStatus.every((s) => s.hasRender);
  const anySceneGenerating = sceneRenderStatus.some((s) => s.isGenerating) || isGeneratingAll;
  const scenesWithoutRenders = sceneRenderStatus.filter((s) => !s.hasRender);

  const isDisabled = !allScenesHaveRenders || anySceneGenerating || renderQueries.isLoading;

  let tooltipMessage = "";
  if (renderQueries.isLoading) {
    tooltipMessage = "Checking scene render status...";
  } else if (anySceneGenerating) {
    tooltipMessage = "Please wait for image generation to complete";
  } else if (!allScenesHaveRenders) {
    tooltipMessage = `${scenesWithoutRenders.length} scene(s) need image generation`;
  }

  if (isDisabled) {
    return (
      <>
        <button
          className="btn-primary w-full py-3 text-base text-center block opacity-50 cursor-not-allowed"
          disabled
          title={tooltipMessage}
        >
          Proceed to Dialogue Editor
        </button>
        <p className="mt-2 text-xs text-amber-600 text-center font-medium">
          {tooltipMessage}
        </p>
        {/* Debug info */}
        {!allScenesHaveRenders && !renderQueries.isLoading && (
          <details className="mt-2 text-xs text-slate-500">
            <summary className="cursor-pointer">Debug: Scene render status</summary>
            <ul className="mt-2 space-y-1">
              {sceneRenderStatus.map((status, idx) => (
                <li key={status.sceneId}>
                  Scene {idx + 1}: {status.hasRender ? "✓ Has render" : "✗ No render"}
                  {status.isGenerating && " (generating...)"}
                </li>
              ))}
            </ul>
          </details>
        )}
      </>
    );
  }

  return (
    <Link
      href="/studio/dialogue"
      className="btn-primary w-full py-3 text-base text-center block"
    >
      Proceed to Dialogue Editor
    </Link>
  );
}

function ScenePromptPanel({
  sceneId,
  onPromptOverrideChange
}: {
  sceneId: string;
  onPromptOverrideChange: (prompt: string | null) => void;
}) {
  const [value, setValue] = useState("");

  // Reset local state when scene changes
  useEffect(() => {
    setValue("");
    // We should also ensure the parent state is reset, but that might cause loops if not careful.
    // Ideally the parent resets it, but here we can just ensure we sync up.
    onPromptOverrideChange(null);
  }, [sceneId, onPromptOverrideChange]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newVal = e.target.value;
    setValue(newVal);
    onPromptOverrideChange(newVal.trim() ? newVal : null);
  };

  return (
    <div className="p-4">
      <h3 className="font-semibold text-ink text-sm mb-2">Prompt Override</h3>
      <p className="text-xs text-slate-500 mb-3">
        Optional: Manually specify the image generation prompt. If left empty,
        the system will generate a prompt based on the scene plan.
      </p>
      <textarea
        className="input w-full h-32 text-sm resize-none"
        placeholder="Enter custom prompt here..."
        value={value}
        onChange={handleChange}
      />
    </div>
  );
}

