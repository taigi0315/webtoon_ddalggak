#!/usr/bin/env python3
"""Create test project/story/scene and print IDs for manual testing."""

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # Create project
    resp = client.post("/v1/projects", json={"name": "demo"})
    if resp.status_code != 200:
        print(f"Failed to create project: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    project_id = resp.json()["project_id"]
    print(f"PROJECT_ID={project_id}")

    # Create story
    resp = client.post(f"/v1/projects/{project_id}/stories", json={"title": "demo story"})
    if resp.status_code != 200:
        print(f"Failed to create story: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    story_id = resp.json()["story_id"]
    print(f"STORY_ID={story_id}")

    # Create scene
    resp = client.post(
        f"/v1/stories/{story_id}/scenes",
        json={"source_text": "A detective enters a rainy alley and spots a mysterious figure."},
    )
    if resp.status_code != 200:
        print(f"Failed to create scene: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    scene_id = resp.json()["scene_id"]
    print(f"SCENE_ID={scene_id}")

    # Export as shell variables
    print("\n# Export for shell (copy-paste):")
    print(f"export PROJECT_ID={project_id}")
    print(f"export STORY_ID={story_id}")
    print(f"export SCENE_ID={scene_id}")


if __name__ == "__main__":
    main()
