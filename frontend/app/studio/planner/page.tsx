"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  fetchScene,
  fetchSceneArtifacts,
  generateLayout,
  generatePanelPlan,
  generatePanelSemantics,
  generateSceneIntent,
  normalizePanelPlan
} from "@/lib/api/queries";
import type { Artifact } from "@/lib/api/types";

const grammarChips = [
  "establish",
  "action",
  "reaction",
  "dialogue",
  "reveal"
];

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
  const [sceneId, setSceneId] = useState("");
  const [panelCount, setPanelCount] = useState(3);

  const sceneQuery = useQuery({
    queryKey: ["scene", sceneId],
    queryFn: () => fetchScene(sceneId),
    enabled: sceneId.length > 0
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

  const sceneStatus = useMemo(() => {
    if (!sceneId) return "Enter a scene ID to load data.";
    if (sceneQuery.isLoading) return "Loading scene...";
    if (sceneQuery.isError) return "Scene load failed.";
    return "Scene loaded.";
  }, [sceneId, sceneQuery.isLoading, sceneQuery.isError]);

  const latestArtifacts = useMemo(() => {
    const list = artifactsQuery.data ?? [];
    return {
      intent: getLatestArtifact(list, "scene_intent"),
      plan: getLatestArtifact(list, "panel_plan"),
      planNormalized: getLatestArtifact(list, "panel_plan_normalized"),
      layout: getLatestArtifact(list, "layout_template"),
      semantics: getLatestArtifact(list, "panel_semantics")
    };
  }, [artifactsQuery.data]);

  const planPayload = (latestArtifacts.planNormalized?.payload ??
    latestArtifacts.plan?.payload) as PanelPlanPayload;
  const layoutPayload = latestArtifacts.layout?.payload as LayoutTemplatePayload | undefined;
  const semanticsPayload = latestArtifacts.semantics?.payload as PanelSemanticsPayload | undefined;

  const panelPlanItems = planPayload?.panels ?? [];
  const layoutPanels = layoutPayload?.panels ?? [];
  const semanticsPanels = semanticsPayload?.panels ?? [];

  return (
    <section className="grid gap-6 xl:grid-cols-[0.9fr_1.4fr_0.9fr]">
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Scene Source</h3>
        <p className="mt-2 text-sm text-slate-500">Linked text for scene planning.</p>
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
            onClick={() => intentMutation.mutate(sceneId)}
            disabled={!sceneId}
          >
            Generate Intent
          </button>
          <button
            className="btn-primary text-xs"
            onClick={() => planMutation.mutate(sceneId)}
            disabled={!sceneId}
          >
            Generate Plan
          </button>
        </div>
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
          <button className="btn-ghost text-xs">Version {latestArtifacts.plan?.version ?? 0}</button>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Panel Plan</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {panelPlanItems.length > 0
              ? panelPlanItems.map((panel, index) => (
                  <span key={`${panel.grammar_id}-${index}`} className="chip">
                    {panel.grammar_id ?? "panel"}
                  </span>
                ))
              : grammarChips.map((chip) => (
                  <span key={chip} className="chip">
                    {chip}
                  </span>
                ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <input
              className="input w-24 text-xs"
              type="number"
              min={1}
              max={12}
              value={panelCount}
              onChange={(event) => setPanelCount(Number(event.target.value))}
            />
            <button
              className="btn-ghost text-xs"
              onClick={() => normalizeMutation.mutate(sceneId)}
              disabled={!sceneId}
            >
              Normalize
            </button>
            <button
              className="btn-primary text-xs"
              onClick={() => semanticsMutation.mutate(sceneId)}
              disabled={!sceneId}
            >
              Generate Semantics
            </button>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Layout Preview</p>
              <p className="mt-1 text-xs text-slate-500">
                {layoutPayload?.template_id ?? "No layout yet"}
              </p>
            </div>
            <button className="btn-ghost text-xs">Template v</button>
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
              onClick={() => layoutMutation.mutate(sceneId)}
              disabled={!sceneId}
            >
              Generate Layout
            </button>
            <button className="btn-primary text-xs">Render Scene Image</button>
          </div>
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
