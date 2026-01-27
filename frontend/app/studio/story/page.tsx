"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  generateStoryBlueprint,
  createProject,
  createStory,
  fetchCharacters,
  fetchProjects,
  fetchScenes,
  fetchStories
} from "@/lib/api/queries";
import type { Character, Scene } from "@/lib/api/types";

type Step = "setup" | "generating" | "review";

// Progress steps for generation
const GENERATION_STEPS = [
  { id: "project", label: "Creating project..." },
  { id: "story", label: "Creating story..." },
  { id: "blueprint", label: "Generating story blueprint..." },
  { id: "complete", label: "Generation complete!" }
];

const BLUEPRINT_MESSAGES = [
  "Splitting story into scenes...",
  "Extracting character profiles...",
  "Normalizing character data...",
  "Planning panel flow...",
  "Resolving layouts...",
  "Drafting panel semantics...",
  "Running QC checks...",
  "Preparing render specs..."
];

export default function StoryEditorPage() {
  const queryClient = useQueryClient();

  // Current step in the flow
  const [step, setStep] = useState<Step>("setup");
  const [generationStep, setGenerationStep] = useState(0);
  const [blueprintMessageIndex, setBlueprintMessageIndex] = useState(0);

  // Setup form state
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [storyTitle, setStoryTitle] = useState("");
  const [storyStyle, setStoryStyle] = useState("default");
  const [imageStyle, setImageStyle] = useState("default");
  const [storyText, setStoryText] = useState("");
  const [storyId, setStoryId] = useState("");
  const [maxScenes, setMaxScenes] = useState(6);

  // Generated results
  const [generatedScenes, setGeneratedScenes] = useState<Scene[]>([]);
  const [generatedCharacters, setGeneratedCharacters] = useState<Character[]>([]);
  const [generationError, setGenerationError] = useState("");

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

  const charactersQuery = useQuery({
    queryKey: ["characters", storyId],
    queryFn: () => fetchCharacters(storyId),
    enabled: storyId.length > 0
  });

  // Mutations
  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      setProjectId(project.project_id);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });

  const createStoryMutation = useMutation({
    mutationFn: createStory,
    onSuccess: (story) => {
      setStoryId(story.story_id);
      queryClient.invalidateQueries({ queryKey: ["stories", projectId] });
    }
  });

  const generateStoryMutation = useMutation({
    mutationFn: generateStoryBlueprint,
    onSuccess: (result) => {
      setGeneratedScenes(result.scenes);
      setGeneratedCharacters(result.characters);
      setGenerationStep(3); // Complete
      setTimeout(() => setStep("review"), 500);
      queryClient.invalidateQueries({ queryKey: ["scenes", storyId] });
      queryClient.invalidateQueries({ queryKey: ["characters", storyId] });
    },
    onError: (error) => {
      setGenerationError(error instanceof Error ? error.message : "Generation failed");
      setStep("setup");
    }
  });

  useEffect(() => {
    if (!generatedScenes.length && scenesQuery.data?.length) {
      setGeneratedScenes(scenesQuery.data);
    }
  }, [generatedScenes.length, scenesQuery.data]);

  useEffect(() => {
    if (!generatedCharacters.length && charactersQuery.data?.length) {
      setGeneratedCharacters(charactersQuery.data);
    }
  }, [generatedCharacters.length, charactersQuery.data]);

  useEffect(() => {
    if (step !== "generating" || generationStep !== 2) return;
    const interval = window.setInterval(() => {
      setBlueprintMessageIndex((prev) => (prev + 1) % BLUEPRINT_MESSAGES.length);
    }, 1800);
    return () => window.clearInterval(interval);
  }, [step, generationStep]);

  // Load from localStorage on mount
  useEffect(() => {
    const storedProjectId = window.localStorage.getItem("lastProjectId") ?? "";
    if (storedProjectId) setProjectId(storedProjectId);
    const storedStoryStyle = window.localStorage.getItem("selectedStoryStyle") ?? "default";
    const storedImageStyle = window.localStorage.getItem("selectedImageStyle") ?? "default";
    setStoryStyle(storedStoryStyle);
    setImageStyle(storedImageStyle);
  }, []);

  // Save projectId to localStorage
  useEffect(() => {
    if (projectId) {
      window.localStorage.setItem("lastProjectId", projectId);
    }
  }, [projectId]);

  // Save storyId to localStorage
  useEffect(() => {
    if (storyId) {
      window.localStorage.setItem("lastStoryId", storyId);
    }
  }, [storyId]);

  // Handle Generate Story - creates project/story if needed, then generates
  const handleGenerateStory = async () => {
    setGenerationError("");
    setStep("generating");
    let currentProjectId = projectId;
    let currentStoryId = storyId;
    setGenerationStep(currentProjectId ? 1 : 0);

    try {
      // Step 1: Create project if needed
      if (!currentProjectId && projectName.trim()) {
        setGenerationStep(0);
        const project = await createProjectMutation.mutateAsync(projectName.trim());
        currentProjectId = project.project_id;
        setProjectId(currentProjectId);
      }

      if (!currentProjectId) {
        throw new Error("Project is required");
      }
      setGenerationStep(1);

      // Step 2: Create story if needed
      if (!currentStoryId && storyTitle.trim()) {
        setGenerationStep(1);
        const story = await createStoryMutation.mutateAsync({
          projectId: currentProjectId,
          title: storyTitle.trim(),
          defaultStoryStyle: storyStyle,
          defaultImageStyle: imageStyle
        });
        currentStoryId = story.story_id;
        setStoryId(currentStoryId);
      }

      if (!currentStoryId) {
        throw new Error("Story title is required");
      }

      // Step 3: Generate story blueprint (this triggers scenes, characters, planning)
      setGenerationStep(2);

      await generateStoryMutation.mutateAsync({
        storyId: currentStoryId,
        sourceText: storyText.trim(),
        maxScenes: maxScenes,
        panelCount: 4,
        maxCharacters: 4,
        generateRenderSpec: true,
        allowAppend: false
      });
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Generation failed");
      setStep("setup");
    }
  };

  const isGenerating = step === "generating";

  const canGenerate =
    (projectId || projectName.trim()) &&
    (storyId || storyTitle.trim()) &&
    storyText.trim() &&
    !isGenerating;

  // GENERATING STEP - Show progress
  if (step === "generating") {
    return (
      <section className="max-w-2xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink text-center">Generating Your Webtoon</h1>
          <p className="mt-2 text-slate-500 text-center">
            Please wait while the AI processes your story...
          </p>
          {generationStep === 2 && (
            <p className="mt-3 text-xs text-indigo-600 text-center">
              {BLUEPRINT_MESSAGES[blueprintMessageIndex]}
            </p>
          )}

          {/* Progress indicator */}
          <div className="mt-8 space-y-4">
            {GENERATION_STEPS.map((stepInfo, index) => {
              const isActive = index === generationStep;
              const isComplete = index < generationStep;
              const isPending = index > generationStep;

              return (
                <div
                  key={stepInfo.id}
                  className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
                    isActive
                      ? "bg-indigo-50 border border-indigo-200"
                      : isComplete
                        ? "bg-green-50 border border-green-200"
                        : "bg-slate-50 border border-slate-100"
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      isActive
                        ? "bg-indigo-500 text-white"
                        : isComplete
                          ? "bg-green-500 text-white"
                          : "bg-slate-200 text-slate-400"
                    }`}
                  >
                    {isComplete ? (
                      <span>&#10003;</span>
                    ) : isActive ? (
                      <span className="animate-spin">&#9696;</span>
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      isActive
                        ? "text-indigo-700 font-medium"
                        : isComplete
                          ? "text-green-700"
                          : "text-slate-400"
                    }`}
                  >
                    {stepInfo.label}
                  </span>
                </div>
              );
            })}
          </div>

          <p className="mt-6 text-xs text-slate-500 text-center">
            This may take 30-60 seconds depending on story length...
          </p>
        </div>
      </section>
    );
  }

  // SETUP STEP - First screen where user sets up the story
  if (step === "setup") {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="surface p-8">
          <h1 className="text-2xl font-bold text-ink">Create Your Webtoon</h1>
          <p className="mt-2 text-slate-500">
            Styles are selected in the Style Select tab before story generation.
          </p>
          <div className="mt-6 rounded-xl border border-[rgba(17,24,39,0.12)] bg-white/70 p-4 text-sm text-slate-600">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Current Styles</p>
            <p className="mt-2">Story style: <strong>{storyStyle}</strong></p>
            <p>Image style: <strong>{imageStyle}</strong></p>
            <Link className="btn-ghost text-xs mt-3 inline-block" href={`/studio/styles?project_id=${projectId}`}>
              Change styles
            </Link>
          </div>

          {/* Project & Story Title */}
          <div className="mt-6 grid gap-6 sm:grid-cols-2">
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
                <option value="">Create new project...</option>
                {projectsQuery.data?.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.name}
                  </option>
                ))}
              </select>
              {!projectId && (
                <input
                  className="input w-full"
                  placeholder="New project name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-ink">Story Title</label>
              {projectId && storiesQuery.data && storiesQuery.data.length > 0 ? (
                <>
                  <select
                    className="input w-full"
                    value={storyId}
                    onChange={(e) => {
                      const nextStoryId = e.target.value;
                      setStoryId(nextStoryId);
                      if (!nextStoryId) {
                        const storedStoryStyle =
                          window.localStorage.getItem("selectedStoryStyle") ?? "default";
                        const storedImageStyle =
                          window.localStorage.getItem("selectedImageStyle") ?? "default";
                        setStoryStyle(storedStoryStyle);
                        setImageStyle(storedImageStyle);
                        return;
                      }
                      const selected = storiesQuery.data?.find(
                        (story) => story.story_id === nextStoryId
                      );
                      if (selected) {
                        setStoryStyle(selected.default_story_style ?? "default");
                        setImageStyle(selected.default_image_style ?? "default");
                      }
                    }}
                  >
                    <option value="">Create new story...</option>
                    {storiesQuery.data.map((story) => (
                      <option key={story.story_id} value={story.story_id}>
                        {story.title}
                      </option>
                    ))}
                  </select>
                  {!storyId && (
                    <input
                      className="input w-full"
                      placeholder="New story title"
                      value={storyTitle}
                      onChange={(e) => setStoryTitle(e.target.value)}
                    />
                  )}
                </>
              ) : (
                <input
                  className="input w-full"
                  placeholder="e.g., Episode 1: The Meeting"
                  value={storyTitle}
                  onChange={(e) => setStoryTitle(e.target.value)}
                />
              )}
            </div>
          </div>

          {/* Max Scenes */}
          <div className="mt-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-ink">Maximum Scenes</label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={2}
                  max={12}
                  value={maxScenes}
                  onChange={(e) => setMaxScenes(Number(e.target.value))}
                  className="flex-1"
                />
                <input
                  className="input w-20 text-center text-sm font-semibold text-indigo-600"
                  type="number"
                  min={2}
                  max={12}
                  value={maxScenes}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    if (Number.isFinite(next)) setMaxScenes(Math.min(12, Math.max(2, next)));
                  }}
                />
              </div>
              <p className="text-xs text-slate-500">
                The AI will split your story into up to {maxScenes} scenes. Recommended: 4-6 for a typical episode.
              </p>
            </div>
          </div>

          {/* Story Text */}
          <div className="mt-6 space-y-2">
            <label className="text-sm font-semibold text-ink">Story Text</label>
            <textarea
              className="textarea w-full min-h-[300px]"
              placeholder="Paste or write your story here. The AI will convert it into webtoon scenes with panels, characters, and dialogue..."
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
            />
            <p className="text-xs text-slate-500">
              Write naturally. The AI will extract scenes, identify characters, and plan the visual panels.
            </p>
          </div>

          {/* Generate Button - ONE button only */}
          <div className="mt-8">
            <button
              className="btn-primary w-full py-3 text-base"
              onClick={handleGenerateStory}
              disabled={!canGenerate}
            >
              Generate Story
            </button>

            {generationError && (
              <p className="mt-3 text-sm text-rose-500 text-center">{generationError}</p>
            )}
          </div>
        </div>
      </section>
    );
  }

  // REVIEW STEP - After generation, show readable results
  return (
    <section className="max-w-4xl mx-auto">
      <div className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Story Generated</h1>
            <p className="mt-1 text-slate-500">
              Review your scenes and characters. Click proceed when ready.
            </p>
          </div>
          <button
            className="btn-ghost text-sm"
            onClick={() => {
              setStep("setup");
              setGeneratedScenes([]);
              setGeneratedCharacters([]);
              setGenerationStep(0);
            }}
          >
            Start Over
          </button>
        </div>

        {/* Scene Summaries */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-ink">
            Scenes ({generatedScenes.length})
          </h2>
          <div className="mt-4 space-y-4">
            {generatedScenes.length === 0 ? (
              <p className="text-slate-500">No scenes generated.</p>
            ) : (
              generatedScenes.map((scene, index) => (
                <div key={scene.scene_id} className="card">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                      <span className="text-sm font-bold text-indigo-600">{index + 1}</span>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-ink">Scene {index + 1}</h3>
                      <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                        {scene.source_text.length > 300
                          ? scene.source_text.slice(0, 300) + "..."
                          : scene.source_text}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Character Profiles */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-ink">
            Characters ({generatedCharacters.length})
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {generatedCharacters.length === 0 ? (
              <p className="text-slate-500 col-span-2">
                No characters were extracted. Try adding more character descriptions to your story.
              </p>
            ) : (
              generatedCharacters.map((character) => (
                <div key={character.character_id} className="card">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-slate-200 flex items-center justify-center">
                      <span className="text-lg font-bold text-slate-500">
                        {character.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-ink">{character.name}</h3>
                      <p className="text-xs text-slate-500 capitalize">{character.role} character</p>
                    </div>
                  </div>
                  {character.description && (
                    <p className="mt-3 text-sm text-slate-600">{character.description}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Proceed Button */}
        <div className="mt-8 pt-6 border-t border-slate-200">
          <Link
            href="/studio/characters"
            className="btn-primary w-full py-3 text-base text-center block"
          >
            Proceed to Character Design
          </Link>
          <p className="mt-3 text-xs text-slate-500 text-center">
            Next: Generate character reference images for visual consistency
          </p>
        </div>
      </div>
    </section>
  );
}
