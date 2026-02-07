/**
 * Shared utility functions for working with artifacts.
 *
 * Consolidates the getLatestArtifact function that was previously
 * duplicated in 3+ components (ScenesPage, SceneCanvas, SceneDialogueList).
 */

import type { Artifact } from "@/lib/api/types";

/**
 * Gets the latest artifact of a given type by version number.
 *
 * @param artifacts - Array of artifacts to search
 * @param type - The artifact type to filter by (e.g. "render_result", "panel_semantics")
 * @returns The latest artifact of the given type, or undefined if not found
 */
export function getLatestArtifact(
  artifacts: Artifact[],
  type: string
): Artifact | undefined {
  return artifacts
    .filter((artifact) => artifact.type === type)
    .sort((a, b) => b.version - a.version)[0];
}
