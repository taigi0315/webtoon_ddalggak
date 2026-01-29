from __future__ import annotations

from .utils import *

def compile_visual_plan_bundle(
    scenes: list[dict],
    characters: list[dict],
    story_style: str | None = None,
) -> list[dict]:
    plans: list[dict] = []
    total = len(scenes)
    for scene in scenes:
        summary = scene.get("summary") or _summarize_text(scene.get("source_text", ""))
        importance = scene.get("scene_importance")
        if not importance:
            idx = scene.get("scene_index") or 1
            if idx == 1:
                importance = "setup"
            elif total and idx == total:
                importance = "cliffhanger"
            else:
                importance = "build"
        plan = {
            "scene_index": scene.get("scene_index"),
            "summary": summary,
            "beats": _extract_beats(scene.get("source_text", ""), max_beats=3),
            "must_show": _extract_must_show(scene.get("source_text", "")),
            "scene_importance": importance,
            "characters": [c.get("name") for c in characters if c.get("name")],
            "story_style": story_style,
        }
        plans.append(plan)
    return plans

def normalize_character_profiles_llm(
    profiles: list[dict],
    source_text: str = "",
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """
    LLM-enhanced character normalization with appearance details.
    Falls back to heuristic normalization if LLM fails.
    """
    if gemini is None or not profiles:
        return normalize_character_profiles(profiles)

    prompt = _prompt_character_normalization(profiles, source_text)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("characters"), list):
        normalized = []
        seen: set[str] = set()
        for char in result["characters"]:
            name = str(char.get("name", "")).strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            # Build identity line if not provided
            identity_line = char.get("identity_line")
            if not identity_line:
                parts = []
                if char.get("age_range"):
                    parts.append(char["age_range"])
                if char.get("gender") and char["gender"] != "unknown":
                    parts.append(char["gender"])
                appearance = char.get("appearance", {})
                if appearance.get("hair"):
                    parts.append(appearance["hair"])
                if appearance.get("build"):
                    parts.append(appearance["build"])
                if char.get("outfit"):
                    parts.append(char["outfit"])
                identity_line = f"{name}: {', '.join(parts)}" if parts else f"{name}: {char.get('role', 'character')}"

            normalized.append({
                "name": name,
                "role": char.get("role", "secondary"),
                "description": char.get("description"),
                "gender": char.get("gender"),
                "age_range": char.get("age_range"),
                "appearance": char.get("appearance"),
                "outfit": char.get("outfit"),
                "identity_line": identity_line,
            })
        if normalized:
            return normalized

    # Fallback to heuristic
    logger.info("Falling back to heuristic character normalization")
    return normalize_character_profiles(profiles)

def run_blind_test_evaluator(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.blind_test_evaluator", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
        if panel_semantics is None:
            raise ValueError("panel_semantics artifact not found")

        semantics_text = _panel_semantics_text(panel_semantics.payload)
        reconstructed = semantics_text
        score = _rough_similarity(scene.source_text, semantics_text)
        comparison = f"Similarity score: {score:.2f}"
        scores = None
        failure_points = []
        repair_suggestions = []

        if gemini is not None:
            # Try two-stage blind test process
            two_stage_success = False

            # Stage 1: Blind reader reconstructs story
            blind_reading = _maybe_json_from_gemini(
                gemini,
                _prompt_blind_reader(panel_semantics.payload),
            )

            if blind_reading and isinstance(blind_reading, dict):
                reconstructed = blind_reading.get("reconstructed_story", reconstructed)

                # Stage 2: Comparator scores the reconstruction
                comparison_result = _maybe_json_from_gemini(
                    gemini,
                    _prompt_comparator(scene.source_text, blind_reading),
                )

                if comparison_result and isinstance(comparison_result, dict):
                    two_stage_success = True
                    comparison = comparison_result.get("comparison", comparison)
                    scores = comparison_result.get("scores")
                    score = float(comparison_result.get("weighted_score", score))
                    failure_points = comparison_result.get("failure_points", [])
                    repair_suggestions = comparison_result.get("repair_suggestions", [])

            # Fallback to single-prompt if two-stage failed
            if not two_stage_success:
                llm = _maybe_json_from_gemini(
                    gemini,
                    _prompt_blind_test(scene.source_text, panel_semantics.payload),
                )
                if isinstance(llm, dict):
                    reconstructed = llm.get("reconstructed_story", reconstructed)
                    comparison = llm.get("comparison", comparison)
                    score = float(llm.get("score", score))
                    scores = llm.get("scores")
                    failure_points = llm.get("failure_points", [])
                    repair_suggestions = llm.get("repair_suggestions", [])

        payload = {
            "reconstructed_story": reconstructed,
            "comparison": comparison,
            "score": score,
            "passed": score >= 0.25,
            "scores": scores,
            "failure_points": failure_points,
            "repair_suggestions": repair_suggestions,
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_BLIND_TEST_REPORT, payload=payload)

def run_panel_semantic_filler(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.panel_semantic_filler", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        story = db.get(Story, scene.story_id)
        characters = _list_characters(db, scene.story_id)

        scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
        scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)

        if panel_plan is None or layout is None:
            raise ValueError("panel_plan and layout_template artifacts are required")

        payload = _heuristic_panel_semantics(
            scene_text=scene.source_text,
            panel_plan=panel_plan.payload,
            layout_template=layout.payload,
            characters=characters,
            story_style=(story.default_story_style if story else None),
            scene_intent=scene_intent,
        )

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_panel_semantics(
                    scene.source_text,
                    panel_plan.payload,
                    layout.payload,
                    characters,
                    scene_intent=scene_intent,
                    genre=(story.default_story_style if story else None),
                ),
            )
            if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                payload["panels"] = llm["panels"]

        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_SEMANTICS, payload=payload)

def compute_scene_chunker(source_text: str, max_scenes: int = 6) -> list[str]:
    text = (source_text or "").strip()
    if not text:
        return []

    max_scenes = max(1, int(max_scenes))

    # Prefer explicit scene/section markers when present.
    marker_split = re.split(r"\n(?=\s*(?:Scene|Chapter|Part)\b)", text, flags=re.IGNORECASE)
    marker_chunks = [p.strip() for p in marker_split if p.strip()]
    if len(marker_chunks) >= 2:
        return marker_chunks[:max_scenes]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(paragraphs) >= 2:
        return _group_chunks(paragraphs, max_scenes)

    sentences = _split_sentences(text)
    if not sentences:
        return [text]

    return _group_chunks(sentences, max_scenes)

def run_panel_plan_generator(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    gemini: GeminiClient | None = None,
):
    with trace_span(
        "graph.panel_plan_generator",
        scene_id=str(scene_id),
        panel_count=panel_count,
    ):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        characters = _list_characters(db, scene.story_id)
        character_names = [c.name for c in characters]
        panel_count = max(1, int(panel_count))
        importance = scene.scene_importance
        if importance:
            panel_count = _panel_count_for_importance(importance, scene.source_text, panel_count)

        # Get scene_intent if available
        scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
        scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None

        # Get QC rules for proactive constraints
        qc_rules_obj = loaders.load_qc_rules_v1()
        qc_rules = {
            "closeup_ratio_max": qc_rules_obj.closeup_ratio_max,
            "dialogue_ratio_max": qc_rules_obj.dialogue_ratio_max,
            "repeated_framing_run_length": qc_rules_obj.repeated_framing_run_length,
        }

        plan = _heuristic_panel_plan(scene.source_text, panel_count)

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_panel_plan(
                    scene.source_text,
                    panel_count,
                    scene_intent=scene_intent,
                    scene_importance=importance,
                    character_names=character_names,
                    qc_rules=qc_rules,
                ),
            )
            if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                plan = {"panels": llm["panels"]}

        plan = _evaluate_and_prune_panel_plan(plan)
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_PLAN, payload=plan)

def run_layout_template_resolver(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.layout_template_resolver", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")

        template = loaders.select_template(panel_plan.payload)
        payload = {
            "template_id": template.template_id,
            "layout_text": template.layout_text,
            "panels": [p.model_dump() for p in template.panels],
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_LAYOUT_TEMPLATE, payload=payload)

def run_qc_checker(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.qc_checker", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)

        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")

        report = _qc_report(panel_plan.payload, panel_semantics.payload if panel_semantics else None)
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_QC_REPORT, payload=report)

def compute_character_profiles(source_text: str, max_characters: int = 6) -> list[dict]:
    text = (source_text or "").strip()
    max_characters = max(1, int(max_characters))

    excluded = _extract_metadata_names(text)
    names = _extract_names(text, excluded=excluded)
    profiles: list[dict] = []
    if not names:
        profiles.append(
            {
                "name": "Protagonist",
                "description": None,
                "role": "main",
                "identity_line": "Protagonist: central character.",
            }
        )
        return profiles

    for idx, name in enumerate(names[:max_characters]):
        role = "main" if idx < 2 else "secondary"
        profiles.append(
            {
                "name": name,
                "description": None,
                "role": role,
                "identity_line": f"{name}: {role} character.",
            }
        )
    return profiles

def normalize_character_profiles(profiles: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    normalized: list[dict] = []
    unnamed_count = 0
    for profile in profiles:
        name = str(profile.get("name") or "").strip()
        if not name:
            unnamed_count += 1
            name = f"Unnamed Character {unnamed_count}"
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        role = (profile.get("role") or "secondary").strip() or "secondary"
        description = profile.get("description")
        identity_line = profile.get("identity_line")
        if not identity_line:
            if description:
                identity_line = f"{name}: {description}"
            else:
                identity_line = f"{name}: {role} character."

        normalized.append(
            {
                "name": name,
                "description": description,
                "role": role,
                "identity_line": identity_line,
            }
        )
    return normalized

def compute_character_profiles_llm(
    source_text: str,
    max_characters: int = 6,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """
    LLM-enhanced character extraction with fallback to heuristic.
    Extracts both explicit and implied characters with evidence.
    """
    if gemini is None:
        return compute_character_profiles(source_text, max_characters)

    prompt = _prompt_character_extraction(source_text, max_characters)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("characters"), list):
        profiles = []
        for char in result["characters"][:max_characters]:
            name = char.get("name", "").strip()
            if not name:
                continue
            profiles.append({
                "name": name,
                "role": char.get("role", "secondary"),
                "description": char.get("relationship_to_main"),
                "evidence_quotes": char.get("evidence_quotes", []),
                "implied": char.get("implied", False),
            })
        if profiles:
            return profiles

    # Fallback to heuristic
    logger.info("Falling back to heuristic character extraction")
    return compute_character_profiles(source_text, max_characters)

def run_dialogue_extractor(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.dialogue_extractor", scene_id=str(scene_id)):
        scene = _get_scene(db, scene_id)
        panel_semantics = ArtifactService(db).get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
        characters = _list_characters(db, scene.story_id)
        character_names = [c.name for c in characters if c.name]
        panel_payload = panel_semantics.payload if panel_semantics else {}
        gemini = None
        try:
            gemini = _build_gemini_client()
        except Exception:  # noqa: BLE001
            gemini = None

        dialogue_script = _generate_dialogue_script(
            scene_id=scene_id,
            scene_text=scene.source_text,
            panel_semantics=panel_payload,
            character_names=character_names,
            gemini=gemini,
        )
        payload = {"dialogue_by_panel": dialogue_script.get("dialogue_by_panel", [])}
        return ArtifactService(db).create_artifact(
            scene_id=scene_id, type=ARTIFACT_DIALOGUE_SUGGESTIONS, payload=payload
        )

def run_panel_plan_normalizer(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.panel_plan_normalizer", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")
        normalized = _normalize_panel_plan(panel_plan.payload)
        return svc.create_artifact(
            scene_id=scene_id, type=ARTIFACT_PANEL_PLAN_NORMALIZED, payload=normalized
        )

def compile_visual_plan_bundle_llm(
    scenes: list[dict],
    characters: list[dict],
    story_style: str | None = None,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """
    LLM-enhanced visual plan compilation with beat extraction.
    Falls back to heuristic compilation if LLM fails.
    """
    if gemini is None:
        return compile_visual_plan_bundle(scenes, characters, story_style)

    prompt = _prompt_visual_plan(scenes, characters, story_style)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("scene_plans"), list):
        plans = []
        global_anchors = result.get("global_environment_anchors", [])

        for scene_plan in result["scene_plans"]:
            scene_idx = scene_plan.get("scene_index")
            # Find matching input scene
            matching_scene = next((s for s in scenes if s.get("scene_index") == scene_idx), None)

            plan = {
                "scene_index": scene_idx,
                "summary": scene_plan.get("summary", ""),
                "scene_importance": scene_plan.get("scene_importance"),
                "beats": scene_plan.get("beats", []),
                "must_show": scene_plan.get("must_show", []),
                "characters": [c.get("name") for c in characters if c.get("name")],
                "story_style": story_style,
                "global_environment_anchors": global_anchors,
            }

            # Preserve source_text from original scene if available
            if matching_scene:
                plan["source_text"] = matching_scene.get("source_text", "")

            plans.append(plan)

        if plans:
            return plans

    # Fallback to heuristic
    logger.info("Falling back to heuristic visual plan compilation")
    return compile_visual_plan_bundle(scenes, characters, story_style)

def run_scene_intent_extractor(
    db: Session,
    scene_id: uuid.UUID,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.scene_intent_extractor", scene_id=str(scene_id), genre=genre):
        scene = _get_scene(db, scene_id)
        story = db.get(Story, scene.story_id)
        characters = _list_characters(db, scene.story_id)
        character_names = [c.name for c in characters]
        summary = _summarize_text(scene.source_text)

        payload = {
            "summary": summary,
            "genre": genre or (story.default_story_style if story else None),
            "setting": _extract_setting(scene.source_text),
            "beats": _extract_beats(scene.source_text, max_beats=3),
            "characters": character_names,
            "logline": None,
            "pacing": "normal",
            "emotional_arc": None,
            "visual_motifs": [],
        }

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_scene_intent(scene.source_text, payload["genre"], character_names),
            )
            if isinstance(llm, dict):
                payload = {**payload, **llm}

        return ArtifactService(db).create_artifact(
            scene_id=scene_id, type=ARTIFACT_SCENE_INTENT, payload=payload
        )
