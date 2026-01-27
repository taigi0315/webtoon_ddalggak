"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchImageStyles, fetchStoryStyles } from "@/lib/api/queries";

export default function StyleSelectorPage() {
  const storyStylesQuery = useQuery({
    queryKey: ["styles", "story"],
    queryFn: fetchStoryStyles
  });

  const imageStylesQuery = useQuery({
    queryKey: ["styles", "image"],
    queryFn: fetchImageStyles
  });

  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <h2 className="text-xl font-semibold text-ink">Select Story Style</h2>
        <p className="mt-1 text-sm text-slate-500">Story genre drives dialogue tone and pacing.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {storyStylesQuery.isLoading && <span className="text-sm text-slate-500">Loading...</span>}
          {storyStylesQuery.isError && <span className="text-sm text-rose-500">Unable to load styles.</span>}
          {storyStylesQuery.data?.map((style) => (
            <button
              key={style.id}
              className="chip"
              title="Apply this story genre style."
            >
              {style.label}
            </button>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">Select Image Style</h2>
            <p className="mt-1 text-sm text-slate-500">Choose the render look for the entire story.</p>
          </div>
          <button className="btn-primary text-xs" title="Apply the selected image style to the story.">
            Apply to Story
          </button>
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
              <div className="h-32 rounded-xl bg-gradient-to-br from-amber-100 via-white to-slate-200" />
              <div>
                <p className="text-sm font-semibold text-ink">{style.label}</p>
                <p className="text-xs text-slate-500">{style.description}</p>
              </div>
              <button className="btn-ghost text-xs" title="Apply this image style to the story.">
                Apply
              </button>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Scene Overrides</h3>
        <p className="mt-1 text-sm text-slate-500">Override style for a single scene if needed.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="card text-sm text-slate-500">Select a story to enable per-scene overrides.</div>
        </div>
      </div>
    </section>
  );
}
