"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  fetchScene,
  fetchStory,
  fetchSceneArtifacts,
  fetchImageStyles,
  evaluateQc,
  generateRender,
  generateRenderSpec,
  generateLayout,
  generatePanelPlan,
  generatePanelSemantics,
  generateSceneIntent,
  normalizePanelPlan
} from "@/lib/api/queries";
import type { Artifact } from "@/lib/api/types";

type PanelPlanPayload = {
  panels?: Array<{ grammar_id?: string; story_function?: string }>;
};

type LayoutTemplatePayload = {
  template_id?: string;
  layout_text?: string;
  panels?: Array<{ x: number; y: number; w: number; h: number }>;
};

type PanelSemanticsPayload = {
  panels?: Array<{ grammar_id?: string; text?: string }>;
};

function getLatestArtifact(artifacts: Artifact[], type: string) {
  return artifacts
    .filter((artifact) => artifact.type === type)
    .sort((a, b) => b.version - a.version)[0];
}

export default function ScenePlannerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [sceneId, setSceneId] = useState("");
  const [panelCount, setPanelCount] = useState(3);
  const [planError, setPlanError] = useState("");
  const [renderError, setRenderError] = useState("");

  const sceneQuery = useQuery({
    queryKey: ["scene", sceneId],
    queryFn: () => fetchScene(sceneId),
    enabled: sceneId.length > 0
  });

  const storyQuery = useQuery({
    queryKey: ["story", sceneQuery.data?.story_id],
    queryFn: () => fetchStory(sceneQuery.data?.story_id ?? ""),
    enabled: !!sceneQuery.data?.story_id
  });

  const imageStylesQuery = useQuery({
    queryKey: ["styles", "image"],
    queryFn: fetchImageStyles
  });

  const artifactsQuery = useQuery({
    queryKey: ["artifacts", sceneId],
    queryFn: () => fetchSceneArtifacts(sceneId),
    enabled: sceneId.length > 0
  });

  const intentMutation = useMutation({
    mutationFn: generateSceneIntent,
    onSuccess: () => artifactsQuery.refetch()
  });

  const planMutation = useMutation({
    mutationFn: (id: string) => generatePanelPlan(id, panelCount),
    onSuccess: () => artifactsQuery.refetch()
  });

  const normalizeMutation = useMutation({
    mutationFn: normalizePanelPlan,
    onSuccess: () => artifactsQuery.refetch()
  });

  const layoutMutation = useMutation({
    mutationFn: generateLayout,
    onSuccess: () => artifactsQuery.refetch()
  });

  const semanticsMutation = useMutation({
    mutationFn: generatePanelSemantics,
    onSuccess: () => artifactsQuery.refetch()
  });

  const qcMutation = useMutation({
    mutationFn: evaluateQc,
    onSuccess: () => artifactsQuery.refetch()
  });

  const renderSpecMutation = useMutation({
    mutationFn: ({ id, styleId }: { id: string; styleId: string }) =>
      generateRenderSpec(id, styleId)
  });

  const renderMutation = useMutation({
    mutationFn: generateRender
  });

  const sceneStatus = useMemo(() => {
    if (!sceneId) return "Enter a scene ID to load data.";
    if (sceneQuery.isLoading) return "Loading scene...";
    if (sceneQuery.isError) return "Scene load failed.";
    return "Scene loaded.";
  }, [sceneId, sceneQuery.isLoading, sceneQuery.isError]);

  useEffect(() => {
    const paramSceneId = searchParams.get("scene_id");
    if (paramSceneId && paramSceneId !== sceneId) {
      setSceneId(paramSceneId);
    }
  }, [sceneId, searchParams]);

  useEffect(() => {
    if (!sceneId && !searchParams.get("scene_id")) {
      const storedSceneId = window.localStorage.getItem("lastSceneId") ?? "";
      if (storedSceneId) setSceneId(storedSceneId);
    }
  }, [sceneId, searchParams]);

  useEffect(() => {
    if (sceneId) {
      window.localStorage.setItem("lastSceneId", sceneId);
    }
  }, [sceneId]);

  const latestArtifacts = useMemo(() => {
    const list = artifactsQuery.data ?? [];
    return {
      intent: getLatestArtifact(list, "scene_intent"),
      plan: getLatestArtifact(list, "panel_plan"),
      planNormalized: getLatestArtifact(list, "panel_plan_normalized"),
      layout: getLatestArtifact(list, "layout_template"),
      semantics: getLatestArtifact(list, "panel_semantics"),
      qc: getLatestArtifact(list, "qc_report")
    };
  }, [artifactsQuery.data]);

  const hasIntent = !!latestArtifacts.intent;
  const hasPlan = !!latestArtifacts.planNormalized || !!latestArtifacts.plan;
  const hasLayout = !!latestArtifacts.layout;
  const hasSemantics = !!latestArtifacts.semantics;
  const canNormalize = !!latestArtifacts.plan;
  const canGenerateLayout = hasPlan;
  const canGenerateSemantics = hasIntent && hasPlan && hasLayout;
  const canRender = hasSemantics;

  const imageStyleIds = imageStylesQuery.data?.map((style) => style.id) ?? [];
  const storyImageStyle = storyQuery.data?.default_image_style ?? "default";
  const renderStyleId = imageStyleIds.includes(storyImageStyle) ? storyImageStyle : "default";

  const planPayload = (latestArtifacts.planNormalized?.payload ??
    latestArtifacts.plan?.payload) as PanelPlanPayload;
  const layoutPayload = latestArtifacts.layout?.payload as LayoutTemplatePayload | undefined;
  const semanticsPayload = latestArtifacts.semantics?.payload as PanelSemanticsPayload | undefined;
  const qcPayload = latestArtifacts.qc?.payload as {
    passed?: boolean;
    issues?: Array<{ code?: string; severity?: string; message?: string }>;
    panel_count?: number;
  } | undefined;
  const qcPassed = qcPayload?.passed === true;

  const panelPlanItems = planPayload?.panels ?? [];
  const layoutPanels = layoutPayload?.panels ?? [];
  const semanticsPanels = semanticsPayload?.panels ?? [];

  return (
    <section className="grid gap-6 xl:grid-cols-[0.9fr_1.4fr_0.9fr]">
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Scene Source</h3>
        <p className="mt-2 text-sm text-slate-500">Linked text for scene planning.</p>
        <p className="mt-1 text-xs text-slate-500">
          Step order: Intent {" > "} Plan {" > "} Layout {" > "} Semantics {" > "} Render.
        </p>
        <input
          className="input mt-4"
          placeholder="Scene ID"
          value={sceneId}
          onChange={(event) => setSceneId(event.target.value)}
        />
        <p className="mt-2 text-xs text-slate-500">{sceneStatus}</p>
        <div className="mt-3 rounded-xl bg-white/70 p-4 text-sm text-slate-600">
          {sceneQuery.data?.source_text ??
            "Enter a scene ID to view source text."}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="btn-ghost text-xs"
            onClick={() => {
              setPlanError("");
              intentMutation.mutate(sceneId);
            }}
            disabled={!sceneId}
            title="Extract the scene intent from the source text."
          >
            {intentMutation.isPending ? "Generating..." : "Generate Intent"}
          </button>
          <button
            className="btn-primary text-xs"
            onClick={async () => {
              if (!sceneId) return;
              setPlanError("");
              try {
                if (!latestArtifacts.intent) {
                  await intentMutation.mutateAsync(sceneId);
                }
                await planMutation.mutateAsync(sceneId);
              } catch (error) {
                setPlanError(error instanceof Error ? error.message : "Plan generation failed");
              }
            }}
            disabled={!sceneId}
            title="Generate a panel plan (auto-creates intent if needed)."
          >
            {planMutation.isPending ? "Generating..." : "Generate Plan"}
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          Generate Plan will create intent automatically if needed.
        </p>
        {planError && <p className="mt-2 text-xs text-rose-500">{planError}</p>}
        {planMutation.isPending && (
          <p className="mt-2 text-[11px] text-slate-500">This can take ~10-20 seconds.</p>
        )}
        <div className="mt-4">
          <p className="text-xs text-slate-500">Latest intent:</p>
          <div className="mt-2 rounded-lg bg-white/70 p-3 text-xs text-slate-600">
            {latestArtifacts.intent?.payload?.summary ?? "No intent yet."}
          </div>
        </div>
      </div>
      <div className="surface p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Plan + Layout</h2>
          <button
            className="btn-ghost text-xs"
            title="View panel plan versions (coming soon)."
          >
            Version {latestArtifacts.plan?.version ?? 0}
          </button>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Panel Plan</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {panelPlanItems.length > 0 ? (
              panelPlanItems.map((panel, index) => (
                <span key={`${panel.grammar_id}-${index}`} className="chip">
                  {panel.grammar_id ?? "panel"}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">No panel plan yet.</span>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <input
              className="input w-24 text-xs"
              type="number"
              min={1}
              max={12}
              value={panelCount}
              onChange={(event) => setPanelCount(Number(event.target.value))}
              title="Set how many panels the plan should target."
            />
            <button
              className="btn-ghost text-xs"
              onClick={() => {
                setPlanError("");
                normalizeMutation.mutate(sceneId);
              }}
              disabled={!sceneId || !canNormalize}
              title="Normalize the panel plan to fit layout rules."
            >
              {normalizeMutation.isPending ? "Normalizing..." : "Normalize"}
            </button>
            <button
              className="btn-primary text-xs"
              onClick={() => {
                setPlanError("");
                semanticsMutation.mutate(sceneId);
              }}
              disabled={!sceneId || !canGenerateSemantics}
              title="Generate semantic descriptions for each panel."
            >
              {semanticsMutation.isPending ? "Generating..." : "Generate Semantics"}
            </button>
          </div>
          {!canGenerateSemantics && sceneId && (
            <p className="mt-2 text-[11px] text-slate-500">
              Requires intent, plan, and layout.
            </p>
          )}
          {semanticsMutation.isPending && (
            <p className="mt-2 text-[11px] text-slate-500">
              Generating semantics can take ~20-30 seconds.
            </p>
          )}
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Layout Preview</p>
              <p className="mt-1 text-xs text-slate-500">
                {layoutPayload?.template_id ?? "No layout yet"}
              </p>
            </div>
            <button className="btn-ghost text-xs" title="Select a different layout template.">
              Template v
            </button>
          </div>
          <div className="mt-4 flex justify-center">
            <div className="relative aspect-[9/16] w-full max-w-xs rounded-2xl bg-white/80 p-2 shadow-soft">
              <div className="relative h-full w-full rounded-xl border border-dashed border-slate-300">
                {layoutPanels.map((panel, index) => (
                  <div
                    key={`${panel.x}-${panel.y}-${index}`}
                    className="absolute rounded-md border-2 border-slate-400/60"
                    style={{
                      left: `${panel.x * 100}%`,
                      top: `${panel.y * 100}%`,
                      width: `${panel.w * 100}%`,
                      height: `${panel.h * 100}%`
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              className="btn-ghost text-xs"
              onClick={() => {
                setPlanError("");
                layoutMutation.mutate(sceneId);
              }}
              disabled={!sceneId || !canGenerateLayout}
              title="Generate a layout grid for the panel plan."
            >
              {layoutMutation.isPending ? "Generating..." : "Generate Layout"}
            </button>
            <button
              className="btn-primary text-xs"
              onClick={async () => {
                if (!sceneId) return;
                setRenderError("");
                try {
                  await qcMutation.mutateAsync(sceneId);
                  const refreshed = await artifactsQuery.refetch();
                  const latestQc = getLatestArtifact(
                    refreshed.data ?? [],
                    "qc_report"
                  );
                  if (!latestQc?.payload?.passed) {
                    setRenderError("QC failed. Fix panel plan or semantics before rendering.");
                    return;
                  }
                  await renderSpecMutation.mutateAsync({ id: sceneId, styleId: renderStyleId });
                  await renderMutation.mutateAsync(sceneId);
                  router.push(`/studio/render?scene_id=${sceneId}`);
                } catch (error) {
                  setRenderError(error instanceof Error ? error.message : "Render failed");
                }
              }}
              disabled={!sceneId || !canRender}
              title="Run QC, compile render spec, then render the scene image."
            >
              Render Scene Image
            </button>
          </div>
          {renderError && <p className="mt-2 text-xs text-rose-500">{renderError}</p>}
          {imageStylesQuery.isError && (
            <p className="mt-2 text-[11px] text-rose-500">
              Unable to load image styles; render will use default.
            </p>
          )}
          {!canRender && sceneId && (
            <p className="mt-2 text-[11px] text-slate-500">
              Requires panel semantics. Generate semantics first.
            </p>
          )}
          {canRender && !qcPassed && (
            <p className="mt-2 text-[11px] text-slate-500">
              QC must pass before rendering. Run QC to see issues.
            </p>
          )}
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Artifacts</p>
          <div className="mt-2 space-y-1 text-xs text-slate-500">
            {artifactsQuery.isLoading && <p>Loading artifacts...</p>}
            {artifactsQuery.isError && <p>Unable to load artifacts.</p>}
            {!artifactsQuery.isLoading &&
              !artifactsQuery.isError &&
              (artifactsQuery.data ?? []).length === 0 && <p>No artifacts yet.</p>}
            {(artifactsQuery.data ?? []).slice(0, 6).map((artifact) => (
              <p key={artifact.artifact_id}>
                {artifact.type} v{artifact.version}
              </p>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">QC Report</p>
            <button
              className="btn-ghost text-xs"
              onClick={() => qcMutation.mutate(sceneId)}
              disabled={!sceneId || !hasSemantics || qcMutation.isPending}
              title="Run quality checks on the panel plan/semantics."
            >
              {qcMutation.isPending ? "Checking..." : "Run QC"}
            </button>
          </div>
          {!hasSemantics && (
            <p className="mt-2 text-[11px] text-slate-500">Generate semantics before QC.</p>
          )}
          {qcPayload ? (
            <div className="mt-3 text-xs text-slate-600">
              <p>Status: {qcPayload.passed ? "passed" : "failed"}</p>
              <p>Panels: {qcPayload.panel_count ?? "-"}</p>
              {(qcPayload.issues ?? []).length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-slate-500">
                  {qcPayload.issues?.map((issue, index) => (
                    <li key={`${issue.code}-${index}`}>
                      [{issue.severity ?? "info"}] {issue.message ?? issue.code}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No QC report yet.</p>
          )}
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Panel Semantics</h3>
        <div className="mt-4 space-y-3">
          {semanticsPanels.length === 0 && (
            <div className="card text-sm text-slate-500">No semantics yet.</div>
          )}
          {semanticsPanels.map((panel, index) => (
            <div key={`${panel.grammar_id}-${index}`} className="card">
              <p className="text-sm font-semibold text-ink">
                Panel {index + 1} - {panel.grammar_id ?? "panel"}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                {panel.text ?? "No description yet."}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
