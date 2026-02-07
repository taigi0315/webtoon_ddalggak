import { describe, it, expect } from "vitest";
import { getLatestArtifact } from "../artifacts";
import type { Artifact } from "@/lib/api/types";

function makeArtifact(
  type: string,
  version: number,
  overrides: Partial<Artifact> = {}
): Artifact {
  return {
    artifact_id: `artifact-${version}`,
    scene_id: "scene-1",
    type,
    version,
    parent_id: null,
    payload: {},
    ...overrides,
  };
}

describe("getLatestArtifact", () => {
  it("returns undefined for empty array", () => {
    expect(getLatestArtifact([], "render_result")).toBeUndefined();
  });

  it("returns undefined when no matching type", () => {
    const artifacts = [
      makeArtifact("panel_plan", 1),
      makeArtifact("panel_plan", 2),
    ];
    expect(getLatestArtifact(artifacts, "render_result")).toBeUndefined();
  });

  it("returns the only matching artifact", () => {
    const artifacts = [
      makeArtifact("panel_plan", 1),
      makeArtifact("render_result", 1),
    ];
    const result = getLatestArtifact(artifacts, "render_result");
    expect(result).toBeDefined();
    expect(result!.type).toBe("render_result");
    expect(result!.version).toBe(1);
  });

  it("returns the highest version for matching type", () => {
    const artifacts = [
      makeArtifact("render_result", 1),
      makeArtifact("render_result", 3),
      makeArtifact("render_result", 2),
    ];
    const result = getLatestArtifact(artifacts, "render_result");
    expect(result).toBeDefined();
    expect(result!.version).toBe(3);
  });

  it("ignores artifacts of different types", () => {
    const artifacts = [
      makeArtifact("panel_plan", 5),
      makeArtifact("render_result", 2),
      makeArtifact("render_result", 1),
    ];
    const result = getLatestArtifact(artifacts, "render_result");
    expect(result!.version).toBe(2);
  });

  it("handles single artifact array", () => {
    const artifacts = [makeArtifact("scene_intent", 1)];
    const result = getLatestArtifact(artifacts, "scene_intent");
    expect(result).toBeDefined();
    expect(result!.type).toBe("scene_intent");
  });

  it("does not mutate the original array", () => {
    const artifacts = [
      makeArtifact("render_result", 1),
      makeArtifact("render_result", 3),
      makeArtifact("render_result", 2),
    ];
    const original = [...artifacts];
    getLatestArtifact(artifacts, "render_result");
    expect(artifacts.map((a) => a.version)).toEqual(
      original.map((a) => a.version)
    );
  });
});
