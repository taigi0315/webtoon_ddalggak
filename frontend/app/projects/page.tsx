"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProject, deleteProject, fetchProjects } from "@/lib/api/queries";

export default function ProjectsPage() {
  const [newProjectName, setNewProjectName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects
  });

  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setNewProjectName("");
      setShowCreate(false);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });

  const createStatus = useMemo(() => {
    if (createMutation.isPending) return "Creating project...";
    if (createMutation.isError) return "Project create failed.";
    return "";
  }, [createMutation.isPending, createMutation.isError]);

  return (
    <section className="space-y-6">
      <div className="surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Project Dashboard</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">My Webtoon Projects</h2>
          </div>
          <div className="flex gap-2">
            <Link
              className="btn-ghost text-xs"
              href="/studio/story"
              title="Create a new story inside a selected project."
            >
              New Story
            </Link>
            <button
              className="btn-primary text-xs"
              onClick={() => setShowCreate((prev) => !prev)}
              title="Create a new project to organize stories and scenes."
            >
              New Project
            </button>
          </div>
        </div>
        {showCreate && (
          <div className="mt-4 card">
            <div className="flex flex-wrap items-center gap-3">
              <input
                className="input flex-1"
                placeholder="Project name"
                value={newProjectName}
                onChange={(event) => setNewProjectName(event.target.value)}
              />
              <button
                className="btn-primary text-xs"
                onClick={() => createMutation.mutate(newProjectName.trim())}
                disabled={!newProjectName.trim()}
                title="Save this new project and open it in the studio."
              >
                Create
              </button>
              <button
                className="btn-ghost text-xs"
                onClick={() => setShowCreate(false)}
                title="Close without creating a project."
              >
                Cancel
              </button>
            </div>
            {createStatus && <p className="mt-2 text-xs text-slate-500">{createStatus}</p>}
          </div>
        )}
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {isLoading && (
            <div className="card text-sm text-slate-500">Loading projects...</div>
          )}
          {error && (
            <div className="card text-sm text-rose-500">
              Unable to load projects. Check the API connection.
            </div>
          )}
          {!isLoading && !error && data?.length === 0 && (
            <div className="card text-sm text-slate-500">
              No projects yet. Create your first project to get started.
            </div>
          )}
          {data?.map((project, index) => (
            <div key={project.project_id} className="card space-y-4">
              <div className="h-32 rounded-xl bg-gradient-to-br from-slate-200 via-white to-amber-100" />
              <div>
                <p className="text-sm font-semibold text-ink">{project.name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {index + 2} scenes rendered - QC passed
                </p>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="pill">Active</span>
                <div className="flex items-center gap-2">
                  <button
                    className="btn-ghost text-xs text-rose-600"
                    onClick={() => {
                      const confirmed = window.confirm(
                        `Delete "${project.name}" and all its stories/scenes?`
                      );
                      if (confirmed) {
                        deleteMutation.mutate(project.project_id);
                      }
                    }}
                    title="Delete this project and all child stories/scenes."
                  >
                    Delete
                  </button>
                  <Link
                    className="btn-ghost text-xs"
                    href={`/studio/story?project_id=${project.project_id}`}
                    title="Open this project in the story editor."
                  >
                    Open
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="surface p-6">
        <h3 className="text-lg font-semibold text-ink">Recent activity</h3>
        <div className="mt-3 text-sm text-slate-500">
          No recent activity yet. Create a story to populate this feed.
        </div>
      </div>
    </section>
  );
}
