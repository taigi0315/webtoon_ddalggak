/**
 * SceneCanvas Component
 * Canvas for editing dialogue bubbles on scene renders
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSceneRenders } from "@/lib/api/queries";
import type { Scene } from "@/lib/api/types";
import { getLatestArtifact } from "@/lib/utils/artifacts";
import { getImageUrl } from "@/lib/utils/media";
import { DialogueBubbleComponent } from "./DialogueBubble";
import { estimateBubbleHeight, mapDialogueTypeToBubbleType } from "./utils";
import type { DialogueBubble, ToolType } from "./types";

interface SceneCanvasProps {
    scene: Scene;
    bubbles: DialogueBubble[];
    onBubbleSelect: (bubbleId: string) => void;
    onBubbleChange: (bubble: DialogueBubble) => void;
    onBubbleAdd: (bubble: DialogueBubble) => void;
    onBubbleDelete: (bubbleId: string) => void;
    activeTool: ToolType;
    zoom: number;
}

export function SceneCanvas({
    scene,
    bubbles,
    onBubbleSelect,
    onBubbleChange,
    onBubbleAdd,
    onBubbleDelete,
    activeTool,
    zoom
}: SceneCanvasProps) {
    const canvasRef = useRef<HTMLDivElement | null>(null);
    const viewportRef = useRef<HTMLDivElement | null>(null);
    const [dragGhost, setDragGhost] = useState<{ x: number; y: number } | null>(null);
    const [draggingBubbleId, setDraggingBubbleId] = useState<string | null>(null);
    const [resizingBubbleId, setResizingBubbleId] = useState<string | null>(null);
    const [tailDraggingId, setTailDraggingId] = useState<string | null>(null);
    const dragOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

    // Handle drag/resize/tail interactions
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

    // Fetch scene render
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

    // Reset scroll on scene change
    useEffect(() => {
        if (viewportRef.current) {
            viewportRef.current.scrollTop = 0;
        }
    }, [scene.scene_id]);

    const handleDrop = (event: React.DragEvent) => {
        event.preventDefault();
        const raw = event.dataTransfer.getData("application/x-dialogue");
        if (!raw || !canvasRef.current) return;

        const data = JSON.parse(raw) as { text: string; speaker?: string; type?: string };
        const rect = canvasRef.current.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width;
        const y = (event.clientY - rect.top) / rect.height;
        const clampedX = Math.max(0.02, Math.min(0.92, x));
        const clampedY = Math.max(0.02, Math.min(0.92, y));

        const bubbleType = mapDialogueTypeToBubbleType(data.type);

        onBubbleAdd({
            id: crypto.randomUUID(),
            panelId: 1,
            bubbleType,
            text: data.text,
            speaker: data.speaker,
            position: { x: clampedX, y: clampedY },
            size: { w: 0.28, h: estimateBubbleHeight(data.text, 0.28) }
        });
        setDragGhost(null);
    };

    const handleClick = (event: React.MouseEvent) => {
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
            bubbleType: "chat",
            text: "New dialogue",
            position: { x: clampedX, y: clampedY },
            size: { w: 0.28, h: estimateBubbleHeight("New dialogue", 0.28) }
        });
    };

    const handleDragStart = (bubbleId: string, offsetX: number, offsetY: number) => {
        dragOffsetRef.current = { x: offsetX, y: offsetY };
        setDraggingBubbleId(bubbleId);
    };

    return (
        <div
            ref={viewportRef}
            className="relative h-full w-full max-w-none overflow-auto rounded-2xl bg-slate-100 shadow-soft"
        >
            <div
                ref={canvasRef}
                className="relative aspect-[9/16] w-full max-w-[680px] rounded-2xl bg-gradient-to-b from-slate-200 via-white to-amber-100 shadow-soft overflow-hidden"
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
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
                onClick={handleClick}
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
                    <DialogueBubbleComponent
                        key={bubble.id}
                        bubble={bubble}
                        activeTool={activeTool}
                        onSelect={onBubbleSelect}
                        onDelete={onBubbleDelete}
                        onDragStart={handleDragStart}
                        onResizeStart={setResizingBubbleId}
                        onTailDragStart={setTailDraggingId}
                        canvasRef={canvasRef}
                    />
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
