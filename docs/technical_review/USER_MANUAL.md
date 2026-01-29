# Ssuljaengi v4 - User Manual

## Introduction

Ssuljaengi v4 is an AI-powered assistant for creating webtoons. It takes your text story and helps you visualize it scene by scene, generating character concept art, storyboards, and final panel images.

## Getting Started

### 1. Create a Project

Everything starts with a **Project**. A project acts as a container for your distinct webtoon series or works.

- Go to the implementation dashboard (via Frontend).
- Click "New Project" and give it a name.

### 2. Add a Story

Within a project, you create a **Story**.

- Paste your full script or webtoon plot into the Story input.
- The AI will automatically analyze it to find **Characters** and **Scenes**.

## Workflow

### Step 1: Character Extraction & Design

Before drawing scenes, the system needs to know who is in them.

- The AI scans your story and creates a list of characters.
- You can review their profiles (Name, Age, Appearance).
- **Action**: Generate visual reference sheets for each character so the AI keeps their look consistent.

### Step 2: Scene Planning

The story is broken down into **Scenes**. For each scene, the AI performs "Planning":

1.  **Intent**: It decides the mood and visual goal of the scene.
2.  **Panel Plan**: It breaks the scene into individual panels (cuts).
3.  **Layout**: It arranges these panels on a page.
4.  **Semantics**: It describes exactly what should be drawn in each panel.

_You can review and edit these plans before rendering._

### Step 3: Scene Rendering

Once the plan is ready, you can **Render** the scene.

- The AI generates high-quality images for each panel.
- It uses the "Character Reference" from Step 1 to ensure your characters look the same.
- **Quality Control (QC)**: The system automatically checks if the image matches the description.

## Features

- **Styles**: You can define a global "Style" (e.g., "Anime", "Noir", "Watercolor") that applies to all images.
- **Export**: You can export your finished scenes as image files or a combined webtoon strip.
- **Blind Test**: The system can run a "Blind Test" where it evaluates its own work to give you a quality report.

## Troubleshooting

- **"QC Failed"**: This means the AI generated an image that didn't match the prompt well enough. You can retry rendering or simplify the scene description.
- **Inconsistent Characters**: Ensure you have generated a good reference image in the Character Library before rendering scenes.
