"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";

import {
  fetchImageStyles,
  fetchStories,
  setStoryStyleDefaults
} from "@/lib/api/queries";

export default function StyleSelectorPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [projectId, setProjectId] = useState("");
  const [storyId, setStoryId] = useState("");
  const [selectedImageStyle, setSelectedImageStyle] = useState("default");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    const paramProjectId = searchParams.get("project_id") ?? "";
    const paramStoryId = searchParams.get("story_id") ?? "";
    const storedImageStyle = window.localStorage.getItem("selectedImageStyle") ?? "default";
    if (paramProjectId) setProjectId(paramProjectId);
    if (paramStoryId) setStoryId(paramStoryId);
    setSelectedImageStyle(storedImageStyle);
  }, [searchParams]);

  const storiesQuery = useQuery({
    queryKey: ["stories", projectId],
    queryFn: () => fetchStories(projectId),
    enabled: projectId.length > 0
  });

  const imageStylesQuery = useQuery({
    queryKey: ["styles", "image"],
    queryFn: fetchImageStyles
  });

  const applyMutation = useMutation({
    mutationFn: setStoryStyleDefaults,
    onSuccess: () => {
      setStatusMessage("Style applied to story.");
      queryClient.invalidateQueries({ queryKey: ["stories", projectId] });
    },
    onError: () => setStatusMessage("Failed to apply style.")
  });

  useEffect(() => {
    if (!storyId || !storiesQuery.data) return;
    const selected = storiesQuery.data.find((story) => story.story_id === storyId);
    if (!selected) return;
    setSelectedImageStyle(selected.default_image_style ?? "default");
  }, [storiesQuery.data, storyId]);

  const persistSelection = (imageStyle: string) => {
    window.localStorage.setItem("selectedImageStyle", imageStyle);
  };

  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <h1 className="text-2xl font-semibold text-ink">Style Select</h1>
        <p className="mt-2 text-sm text-slate-500">
          Pick your image style. We'll remember it for the Story Editor.
        </p>
      </div>

      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">Select Image Style</h2>
            <p className="mt-1 text-sm text-slate-500">Choose the render look for the entire story.</p>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {imageStylesQuery.isLoading && (
            <div className="card text-sm text-slate-500">Loading styles...</div>
          )}
          {imageStylesQuery.isError && (
            <div className="card text-sm text-rose-500">Unable to load styles.</div>
          )}
          {imageStylesQuery.data?.map((style) => (
            <div key={style.id} className="card space-y-3">
              <div className="h-32 rounded-xl overflow-hidden bg-slate-100">
                {style.image_url ? (
                  <img
                    src={style.image_url}
                    alt={style.label}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="h-full w-full bg-gradient-to-br from-amber-100 via-white to-slate-200" />
                )}
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">{style.label}</p>
                <p className="text-xs text-slate-500">{style.description}</p>
              </div>
              <button
                className="btn-ghost text-xs"
                title="Apply this image style to the story."
                onClick={() => {
                  setSelectedImageStyle(style.id);
                  persistSelection(style.id);
                }}
              >
                {selectedImageStyle === style.id ? "Selected" : "Apply"}
              </button>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">Ready to write?</p>
            <p className="text-xs text-slate-500">
              Continue to the Story Editor to create your story with this style.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {storyId && (
              <button
                className="btn-ghost text-xs"
                onClick={() => {
                  persistSelection(selectedImageStyle);
                  applyMutation.mutate({
                    storyId,
                    defaultImageStyle: selectedImageStyle
                  });
                }}
                disabled={applyMutation.isPending}
              >
                Apply Style to Story
              </button>
            )}
            <button
              className="btn-primary text-xs"
              onClick={() => {
                persistSelection(selectedImageStyle);
                const params = new URLSearchParams();
                if (projectId) params.set("project_id", projectId);
                if (storyId) params.set("story_id", storyId);
                router.push(`/studio/story?${params.toString()}`);
              }}
            >
              Story Editor
            </button>
            {statusMessage && <span className="text-xs text-slate-500">{statusMessage}</span>}
          </div>
        </div>
      </div>
    </section>
  );
}
