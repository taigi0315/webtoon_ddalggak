/**
 * SceneDialogueList Component
 * Displays draggable dialogue suggestions for a scene
 */

"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    fetchDialogueSuggestions,
    fetchSceneArtifacts
} from "@/lib/api/queries";
import type { Artifact, DialogueLine, DialoguePanel } from "@/lib/api/types";

function getLatestArtifact(artifacts: Artifact[], type: string) {
    return artifacts
        .filter((artifact) => artifact.type === type)
        .sort((a, b) => b.version - a.version)[0];
}

interface SceneDialogueListProps {
    sceneId: string;
}

export function SceneDialogueList({ sceneId }: SceneDialogueListProps) {
    const suggestionsQuery = useQuery({
        queryKey: ["dialogue-suggestions", sceneId],
        queryFn: () => fetchDialogueSuggestions(sceneId),
        enabled: sceneId.length > 0
    });

    const artifactsQuery = useQuery({
        queryKey: ["scene-artifacts", sceneId],
        queryFn: () => fetchSceneArtifacts(sceneId),
        enabled: sceneId.length > 0
    });

    const panelPurposeMap = useMemo(() => {
        const artifacts = artifactsQuery.data ?? [];
        const panelPlan =
            getLatestArtifact(artifacts, "panel_plan_normalized") ??
            getLatestArtifact(artifacts, "panel_plan");
        const panels = panelPlan?.payload?.panels ?? [];
        const map = new Map<number, { purpose?: string; role?: string; hasDialogue?: boolean }>();
        if (Array.isArray(panels)) {
            panels.forEach((panel: any) => {
                if (typeof panel?.panel_index === "number") {
                    map.set(panel.panel_index, {
                        purpose: panel.panel_purpose,
                        role: panel.panel_role,
                        hasDialogue: panel.has_dialogue
                    });
                }
            });
        }
        return map;
    }, [artifactsQuery.data]);

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

    const panels: DialoguePanel[] = suggestionsQuery.data?.dialogue_by_panel ?? [];

    if (panels.length === 0) {
        return <div className="card text-sm text-slate-500">No dialogue lines found.</div>;
    }

    return (
        <div className="space-y-4">
            {panels.map((panel) => (
                <div key={`panel-${panel.panel_id}`} className="card space-y-3">
                    <div className="flex items-center justify-between">
                        <p className="text-[11px] uppercase tracking-[0.3em] text-slate-400">
                            Panel {panel.panel_id}
                        </p>
                        {panelPurposeMap.get(panel.panel_id)?.purpose && (
                            <div className="flex items-center gap-2 text-[10px] text-slate-500">
                                <span className="rounded-full bg-slate-100 px-2 py-0.5 uppercase tracking-[0.2em]">
                                    {panelPurposeMap.get(panel.panel_id)?.purpose}
                                </span>
                                {panelPurposeMap.get(panel.panel_id)?.role && (
                                    <span className="rounded-full bg-slate-100 px-2 py-0.5 uppercase tracking-[0.2em]">
                                        {panelPurposeMap.get(panel.panel_id)?.role}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                    {panel.lines.length === 0 && (
                        <p className="text-xs text-slate-500">No dialogue for this panel.</p>
                    )}
                    {panel.lines.map((line: DialogueLine, idx: number) => (
                        <div
                            key={`${panel.panel_id}-${idx}-${line.speaker}`}
                            className="rounded-lg border border-slate-200 bg-white/80 px-3 py-2 text-xs text-slate-600 cursor-grab active:cursor-grabbing"
                            draggable
                            onDragStart={(event) => {
                                event.dataTransfer.setData(
                                    "application/x-dialogue",
                                    JSON.stringify({
                                        text: line.text,
                                        speaker: line.speaker,
                                        type: line.type  // Preserve bubble type (SFX, thought, etc)
                                    })
                                );
                                event.dataTransfer.effectAllowed = "copy";
                            }}
                        >
                            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
                                {line.type}
                            </p>
                            <p className="mt-1 font-semibold text-ink">{line.speaker}</p>
                            <p className="mt-1 text-slate-600">{line.text}</p>
                            <p className="mt-2 text-[11px] text-slate-400">
                                Drag this line onto the canvas.
                            </p>
                        </div>
                    ))}
                </div>
            ))}
        </div>
    );
}
