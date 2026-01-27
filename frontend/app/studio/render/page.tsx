"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  fetchScene,
  fetchSceneArtifacts,
  fetchSceneRenders,
  fetchStory,
  fetchImageStyles,
  evaluateQc,
  generateRender,
  generateRenderSpec
} from "@/lib/api/queries";
import type { Artifact } from "@/lib/api/types";

function getLatestArtifact(artifacts: Artifact[], type: string) {
  return artifacts
    .filter((artifact) => artifact.type === type)
    .sort((a, b) => b.version - a.version)[0];
}

export default function SceneRendererPage() {
  const searchParams = useSearchParams();
  const [sceneId, setSceneId] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const paramSceneId = searchParams.get("scene_id") ?? "";
    if (paramSceneId && paramSceneId !== sceneId) {
      setSceneId(paramSceneId);
      window.localStorage.setItem("lastSceneId", paramSceneId);
    }
  }, [sceneId, searchParams]);

  useEffect(() => {
    if (!sceneId && !searchParams.get("scene_id")) {
      const storedSceneId = window.localStorage.getItem("lastSceneId") ?? "";
      if (storedSceneId) setSceneId(storedSceneId);
    }
  }, [sceneId, searchParams]);

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

  const rendersQuery = useQuery({
    queryKey: ["renders", sceneId],
    queryFn: () => fetchSceneRenders(sceneId),
    enabled: sceneId.length > 0
  });

  const renderSpecMutation = useMutation({
    mutationFn: ({ id, styleId }: { id: string; styleId: string }) =>
      generateRenderSpec(id, styleId)
  });

  const qcMutation = useMutation({
    mutationFn: evaluateQc,
    onSuccess: () => artifactsQuery.refetch()
  });

  const renderMutation = useMutation({
    mutationFn: generateRender,
    onSuccess: () => rendersQuery.refetch()
  });

  const latestRender = useMemo(() => {
    const list = rendersQuery.data ?? [];
    return getLatestArtifact(list, "render_result");
  }, [rendersQuery.data]);

  const latestSemantics = useMemo(() => {
    const list = artifactsQuery.data ?? [];
    return getLatestArtifact(list, "panel_semantics");
  }, [artifactsQuery.data]);

  const latestQc = useMemo(() => {
    const list = artifactsQuery.data ?? [];
    return getLatestArtifact(list, "qc_report");
  }, [artifactsQuery.data]);

  const qcPassed = latestQc?.payload?.passed === true;
  const imageStyleIds = imageStylesQuery.data?.map((style) => style.id) ?? [];
  const storyImageStyle = storyQuery.data?.default_image_style ?? "default";
  const renderStyleId = imageStyleIds.includes(storyImageStyle) ? storyImageStyle : "default";
  const canRender = !!sceneId && !!latestSemantics;

  return (
    <section className="grid gap-6 xl:grid-cols-[0.7fr_1.6fr_0.7fr]">
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Render History</h3>
        <div className="mt-4 space-y-3">
          {rendersQuery.isLoading && (
            <div className="card text-sm text-slate-500">Loading renders...</div>
          )}
          {rendersQuery.isError && (
            <div className="card text-sm text-rose-500">Unable to load renders.</div>
          )}
          {(rendersQuery.data ?? []).length === 0 && !rendersQuery.isLoading && (
            <div className="card text-sm text-slate-500">No renders yet.</div>
          )}
          {(rendersQuery.data ?? []).map((render, index) => (
            <div key={render.artifact_id} className="card flex items-center gap-3">
              <div className="h-14 w-10 rounded-lg bg-gradient-to-b from-slate-200 to-white" />
              <div>
                <p className="text-sm font-semibold text-ink">v{render.version}</p>
                <p className="text-xs text-slate-500">Artifact {index + 1}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">Scene Render</h2>
            <p className="mt-1 text-xs text-slate-500">Scene ID: {sceneId || "-"}</p>
          </div>
          <div className="flex gap-2">
            <button className="btn-ghost text-xs" title="Toggle panel overlay (coming soon).">
              Panel Overlay
            </button>
            <button className="btn-ghost text-xs" title="Zoom controls (coming soon).">
              Zoom
            </button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          {latestRender?.payload?.image_url ? (
            <img
              className="aspect-[9/16] w-full max-w-md rounded-2xl object-cover shadow-soft"
              src={String(latestRender.payload.image_url)}
              alt="Scene render"
            />
          ) : (
            <div className="aspect-[9/16] w-full max-w-md rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft" />
          )}
        </div>
        {errorMessage && <p className="text-xs text-rose-500">{errorMessage}</p>}
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-ghost text-xs"
            onClick={async () => {
              if (!sceneId) return;
              setErrorMessage("");
              try {
                await renderSpecMutation.mutateAsync({ id: sceneId, styleId: renderStyleId });
              } catch (error) {
                setErrorMessage(error instanceof Error ? error.message : "RenderSpec failed");
              }
            }}
            disabled={!sceneId}
            title="Compile the render spec from the current scene artifacts."
          >
            Compile RenderSpec
          </button>
          <button
            className="btn-primary text-xs"
            onClick={async () => {
              if (!sceneId) return;
              setErrorMessage("");
              try {
                await qcMutation.mutateAsync(sceneId);
                const refreshed = await artifactsQuery.refetch();
                const qcReport = getLatestArtifact(refreshed.data ?? [], "qc_report");
                if (!qcReport?.payload?.passed) {
                  setErrorMessage("QC failed. Fix panel plan or semantics before rendering.");
                  return;
                }
                await renderSpecMutation.mutateAsync({ id: sceneId, styleId: renderStyleId });
                await renderMutation.mutateAsync(sceneId);
              } catch (error) {
                setErrorMessage(error instanceof Error ? error.message : "Render failed");
              }
            }}
            disabled={!canRender}
            title="Run QC, compile render spec, then render the scene image."
          >
            Render
          </button>
          <button
            className="btn-ghost text-xs"
            onClick={async () => {
              if (!sceneId) return;
              setErrorMessage("");
              try {
                await qcMutation.mutateAsync(sceneId);
                const refreshed = await artifactsQuery.refetch();
                const qcReport = getLatestArtifact(refreshed.data ?? [], "qc_report");
                if (!qcReport?.payload?.passed) {
                  setErrorMessage("QC failed. Fix panel plan or semantics before rendering.");
                  return;
                }
                await renderMutation.mutateAsync(sceneId);
              } catch (error) {
                setErrorMessage(error instanceof Error ? error.message : "Regenerate failed");
              }
            }}
            disabled={!canRender}
            title="Re-render the latest scene (QC must pass)."
          >
            Regenerate
          </button>
          <button
            className="btn-primary text-xs"
            disabled={!latestRender}
            title="Approve the selected render."
          >
            Approve
          </button>
        </div>
        {!canRender && sceneId && (
          <p className="text-[11px] text-slate-500">Requires panel semantics before rendering.</p>
        )}
        {imageStylesQuery.isError && (
          <p className="text-[11px] text-rose-500">
            Unable to load image styles; render will use default.
          </p>
        )}
        {canRender && !qcPassed && (
          <p className="text-[11px] text-slate-500">
            QC must pass before rendering. Run QC in Scene Design.
          </p>
        )}
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Blind Test</h3>
        <div className="mt-4 space-y-3">
          <div className="card text-sm text-slate-500">No blind test results yet.</div>
        </div>
      </div>
    </section>
  );
}
