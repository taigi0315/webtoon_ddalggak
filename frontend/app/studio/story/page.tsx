"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  autoChunkScenes,
  createScene,
  createStory,
  fetchImageStyles,
  fetchProjects,
  fetchScenes,
  fetchStories,
  fetchStoryStyles
} from "@/lib/api/queries";

export default function StoryEditorPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [projectId, setProjectId] = useState("");
  const [storyTitle, setStoryTitle] = useState("");
  const [storyStyle, setStoryStyle] = useState("default");
  const [imageStyle, setImageStyle] = useState("default");
  const [storyId, setStoryId] = useState("");
  const [sceneText, setSceneText] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [maxScenes, setMaxScenes] = useState(6);
  const [lastChunkCount, setLastChunkCount] = useState<number | null>(null);

  const createStoryMutation = useMutation({
    mutationFn: createStory,
    onSuccess: (story) => {
      setStoryId(story.story_id);
      queryClient.invalidateQueries({ queryKey: ["stories", projectId] });
    }
  });

  const createSceneMutation = useMutation({
    mutationFn: createScene,
    onSuccess: (scene) => {
      setSceneId(scene.scene_id);
      queryClient.invalidateQueries({ queryKey: ["scenes", storyId] });
    }
  });

  const autoChunkMutation = useMutation({
    mutationFn: autoChunkScenes,
    onSuccess: (scenes) => {
      setLastChunkCount(scenes.length);
      if (scenes.length > 0) {
        setSceneId(scenes[0].scene_id);
      }
      queryClient.invalidateQueries({ queryKey: ["scenes", storyId] });
    }
  });

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

  const storyStylesQuery = useQuery({
    queryKey: ["styles", "story"],
    queryFn: fetchStoryStyles
  });

  const imageStylesQuery = useQuery({
    queryKey: ["styles", "image"],
    queryFn: fetchImageStyles
  });

  const storyError = useMemo(() => {
    if (!createStoryMutation.isError) return "";
    return createStoryMutation.error instanceof Error
      ? createStoryMutation.error.message
      : "Story create failed";
  }, [createStoryMutation.error, createStoryMutation.isError]);

  const sceneError = useMemo(() => {
    if (!createSceneMutation.isError) return "";
    return createSceneMutation.error instanceof Error
      ? createSceneMutation.error.message
      : "Scene create failed";
  }, [createSceneMutation.error, createSceneMutation.isError]);

  const storyStatus = createStoryMutation.isPending
    ? "Creating story..."
    : storyError
      ? `Story create failed: ${storyError}`
      : storyId
        ? `Story ready: ${storyId}`
        : "No story created yet";

  const sceneStatus = createSceneMutation.isPending
    ? "Creating scene..."
    : sceneError
      ? `Scene create failed: ${sceneError}`
      : sceneId
        ? `Scene ready: ${sceneId}`
        : "No scene created yet";

  useEffect(() => {
    const paramProjectId = searchParams.get("project_id") ?? "";
    const paramStoryId = searchParams.get("story_id") ?? "";
    if (paramProjectId && paramProjectId !== projectId) {
      setProjectId(paramProjectId);
    }
    if (paramStoryId && paramStoryId !== storyId) {
      setStoryId(paramStoryId);
    }
  }, [projectId, searchParams, storyId]);

  useEffect(() => {
    if (!projectId && !searchParams.get("project_id")) {
      const storedProjectId = window.localStorage.getItem("lastProjectId") ?? "";
      if (storedProjectId) setProjectId(storedProjectId);
    }
    if (!storyId && !searchParams.get("story_id")) {
      const storedStoryId = window.localStorage.getItem("lastStoryId") ?? "";
      if (storedStoryId) setStoryId(storedStoryId);
    }
  }, [projectId, searchParams, storyId]);

  useEffect(() => {
    if (projectId) {
      window.localStorage.setItem("lastProjectId", projectId);
    }
  }, [projectId]);

  useEffect(() => {
    if (storyId) {
      window.localStorage.setItem("lastStoryId", storyId);
    }
  }, [storyId]);

  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Story Editor + Scene Builder</h2>
          <button
            className="btn-primary text-xs"
            onClick={() =>
              createStoryMutation.mutate({
                projectId: projectId.trim(),
                title: storyTitle.trim(),
                defaultStoryStyle: storyStyle.trim(),
                defaultImageStyle: imageStyle.trim()
              })
            }
            disabled={!projectId || !storyTitle}
            title="Create the story (episode) container for scenes."
          >
            Create Story
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-500">
          Paste the chapter draft and extract multiple scenes with AI chunking.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Step order: project {" > "} story {" > "} scenes {" > "} character design {" > "} scene design {" > "} render.
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Use Create Scenes to split long story text into multiple scenes.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <select
            className="input"
            value={projectId}
            onChange={(event) => {
              setProjectId(event.target.value);
              setStoryId("");
              setSceneId("");
              const nextProjectId = event.target.value;
              if (nextProjectId) {
                router.push(`/studio/story?project_id=${nextProjectId}`);
              } else {
                router.push("/studio/story");
              }
            }}
          >
            <option value="">Select project</option>
            {projectsQuery.data?.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {projectsQuery.isLoading && "Loading projects..."}
            {projectsQuery.isError && "Unable to load projects."}
            <button
              className="btn-ghost text-[11px]"
              type="button"
              onClick={() => projectsQuery.refetch()}
              title="Reload projects from the API."
            >
              Refresh
            </button>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500">Story title</label>
            <input
              className="input"
              placeholder="Ex: Blue Couch Reunion"
              value={storyTitle}
              onChange={(event) => setStoryTitle(event.target.value)}
            />
            <p className="text-[11px] text-slate-500">This is the story title shown in the studio.</p>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500">Story style (genre)</label>
            <select
              className="input"
              value={storyStyle}
              onChange={(event) => setStoryStyle(event.target.value)}
            >
              {!storyStylesQuery.data && <option value="default">Default</option>}
              {storyStylesQuery.data?.map((style) => (
                <option key={style.id} value={style.id}>
                  {style.label}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500">
              {storyStylesQuery.data?.find((style) => style.id === storyStyle)?.description ??
                "Select the genre that guides the scene intent."}
            </p>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500">Image style</label>
            <select
              className="input"
              value={imageStyle}
              onChange={(event) => setImageStyle(event.target.value)}
            >
              {!imageStylesQuery.data && <option value="default">Default</option>}
              {imageStylesQuery.data?.map((style) => (
                <option key={style.id} value={style.id}>
                  {style.label}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500">
              {imageStylesQuery.data?.find((style) => style.id === imageStyle)?.description ??
                "Select the rendering style for the story."}
            </p>
          </div>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <select
            className="input"
            value={storyId}
            onChange={(event) => {
              setStoryId(event.target.value);
              setSceneId("");
              const nextStoryId = event.target.value;
              const params = new URLSearchParams();
              if (projectId) params.set("project_id", projectId);
              if (nextStoryId) params.set("story_id", nextStoryId);
              router.push(`/studio/story?${params.toString()}`);
            }}
            disabled={!projectId || storiesQuery.isLoading}
          >
            <option value="">Select story</option>
            {storiesQuery.data?.map((story) => (
              <option key={story.story_id} value={story.story_id}>
                {story.title}
              </option>
            ))}
          </select>
          <div className="text-xs text-slate-500">
            {storiesQuery.isLoading && "Loading stories..."}
            {storiesQuery.isError && "Unable to load stories."}
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">{storyStatus}</p>
        <textarea
          className="textarea mt-4"
          placeholder="Story draft or single scene text..."
          value={sceneText}
          onChange={(event) => setSceneText(event.target.value)}
        />
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <label htmlFor="max-scenes" className="text-[11px] uppercase tracking-[0.2em]">
              Max scenes
            </label>
            <input
              id="max-scenes"
              className="input w-20 text-xs"
              type="number"
              min={1}
              max={12}
              value={maxScenes}
              onChange={(event) => {
                const nextValue = Number(event.target.value);
                setMaxScenes(Number.isFinite(nextValue) && nextValue > 0 ? nextValue : 1);
              }}
              title="Limit how many scenes Auto Chunk will create."
            />
          </div>
          <button
            className="btn-primary text-xs"
            onClick={() => {
              setLastChunkCount(null);
              autoChunkMutation.mutate({
                storyId: storyId.trim(),
                sourceText: sceneText.trim(),
                maxScenes
              });
            }}
            disabled={!storyId || !sceneText || autoChunkMutation.isPending}
            title="Split the story into multiple scenes (recommended)."
          >
            {autoChunkMutation.isPending ? "Chunking..." : "Create Scenes"}
          </button>
          <button
            className="btn-ghost text-xs"
            onClick={() => {
              setLastChunkCount(null);
              createSceneMutation.mutate({
                storyId: storyId.trim(),
                sourceText: sceneText.trim()
              });
            }}
            disabled={!storyId || !sceneText}
            title="Create a single scene from the selected text."
          >
            Create Single Scene
          </button>
          <button className="btn-ghost text-xs" title="Highlight beats in the text (coming soon).">
            Highlight Beats
          </button>
        </div>
        {autoChunkMutation.isError && (
          <p className="mt-2 text-xs text-rose-500">
            {autoChunkMutation.error instanceof Error
              ? autoChunkMutation.error.message
              : "Auto chunk failed"}
          </p>
        )}
        {lastChunkCount !== null && !autoChunkMutation.isPending && (
          <p className="mt-2 text-xs text-slate-500">
            Created {lastChunkCount} scene{lastChunkCount === 1 ? "" : "s"} from this story.
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">{sceneStatus}</p>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">Scenes</h3>
          <Link
            className="btn-ghost text-xs"
            href="/studio/characters"
            title="Jump to Character Design after scenes are created."
          >
            Character Design
          </Link>
        </div>
        <div className="mt-4 space-y-3">
          {!storyId && (
            <div className="card text-sm text-slate-500">Select a story to view scenes.</div>
          )}
          {storyId && scenesQuery.isLoading && (
            <div className="card text-sm text-slate-500">Loading scenes...</div>
          )}
          {storyId && scenesQuery.isError && (
            <div className="card text-sm text-rose-500">Unable to load scenes.</div>
          )}
          {storyId && scenesQuery.data?.length === 0 && (
            <div className="card text-sm text-slate-500">No scenes created yet.</div>
          )}
          {scenesQuery.data?.map((scene, index) => (
            <div key={scene.scene_id} className="card flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-ink">Scene {index + 1}</p>
                <p className="mt-1 text-xs text-slate-500">{scene.scene_id}</p>
              </div>
              <Link
                className="btn-ghost text-xs"
                href={`/studio/planner?scene_id=${scene.scene_id}`}
                title="Open this scene in Scene Design (panels, layout, semantics)."
              >
                Design Panels
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
