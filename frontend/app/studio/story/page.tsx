"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { createScene, createStory, fetchProjects, fetchScenes, fetchStories } from "@/lib/api/queries";

export default function StoryEditorPage() {
  const [projectId, setProjectId] = useState("");
  const [storyTitle, setStoryTitle] = useState("Blue Couch Reunion");
  const [storyStyle, setStoryStyle] = useState("romance");
  const [imageStyle, setImageStyle] = useState("soft_webtoon");
  const [storyId, setStoryId] = useState("");
  const [sceneText, setSceneText] = useState(
    "Min-ji enters the room looking worried. Ji-hoon turns from the window, the city lights behind him."
  );
  const [sceneId, setSceneId] = useState("");

  const createStoryMutation = useMutation({
    mutationFn: createStory,
    onSuccess: (story) => {
      setStoryId(story.story_id);
    }
  });

  const createSceneMutation = useMutation({
    mutationFn: createScene,
    onSuccess: (scene) => {
      setSceneId(scene.scene_id);
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

  const storyStatus = createStoryMutation.isPending
    ? "Creating story..."
    : createStoryMutation.isError
      ? "Story create failed"
      : storyId
        ? `Story ready: ${storyId}`
        : "No story created yet";

  const sceneStatus = createSceneMutation.isPending
    ? "Creating scene..."
    : createSceneMutation.isError
      ? "Scene create failed"
      : sceneId
        ? `Scene ready: ${sceneId}`
        : "No scene created yet";

  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-ink">Story Editor</h2>
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
          >
            Create Story
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-500">
          Paste the chapter draft and extract scenes with QC-ready chunking.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <select
            className="input"
            value={projectId}
            onChange={(event) => {
              setProjectId(event.target.value);
              setStoryId("");
              setSceneId("");
            }}
          >
            <option value="">Select project</option>
            {projectsQuery.data?.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))}
          </select>
          <input
            className="input"
            placeholder="Story title"
            value={storyTitle}
            onChange={(event) => setStoryTitle(event.target.value)}
          />
          <input
            className="input"
            placeholder="Default story style (ex: romance)"
            value={storyStyle}
            onChange={(event) => setStoryStyle(event.target.value)}
          />
          <input
            className="input"
            placeholder="Default image style (ex: soft_webtoon)"
            value={imageStyle}
            onChange={(event) => setImageStyle(event.target.value)}
          />
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <select
            className="input"
            value={storyId}
            onChange={(event) => {
              setStoryId(event.target.value);
              setSceneId("");
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
          placeholder="Scene text goes here..."
          value={sceneText}
          onChange={(event) => setSceneText(event.target.value)}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="btn-ghost text-xs">Auto Chunk</button>
          <button className="btn-ghost text-xs">Highlight Beats</button>
          <button
            className="btn-primary text-xs"
            onClick={() =>
              createSceneMutation.mutate({
                storyId: storyId.trim(),
                sourceText: sceneText.trim()
              })
            }
            disabled={!storyId || !sceneText}
          >
            Create Scene
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-500">{sceneStatus}</p>
      </div>
      <div className="surface p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">Scenes</h3>
          <button className="btn-ghost text-xs">New Scene</button>
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
              <button className="btn-ghost text-xs">Open</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
