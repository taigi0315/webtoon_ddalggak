"""Integration tests for Art Director in the workflow.

Tests that Art Director is called in the correct order and creates artifacts.
"""

import pytest
import uuid
from unittest.mock import Mock, patch

from app.db.session import get_sessionmaker
from app.graphs.nodes.planning.art_direction import run_art_director
from app.graphs.nodes.constants import ARTIFACT_ART_DIRECTION
from app.services.artifacts import ArtifactService


class TestArtDirectorIntegration:
    """Integration tests for Art Director in workflow.
    
    Validates: Requirements 5.1
    """
    
    def test_art_director_creates_artifact(self):
        """Test that Art Director creates an artifact with correct type."""
        from app.db.models import Scene, Story, Project
        
        SessionLocal = get_sessionmaker()
        with SessionLocal() as db_session:
            # Create test data
            project = Project(name="Test Project")
            db_session.add(project)
            db_session.flush()
            
            story = Story(
                project_id=project.project_id,
                title="Test Story",
            )
            db_session.add(story)
            db_session.flush()
            
            scene = Scene(
                story_id=story.story_id,
                source_text="A tense confrontation in a dark alley.",
            )
            db_session.add(scene)
            db_session.flush()
            
            # Run Art Director (without Gemini, will use fallback)
            artifact = run_art_director(
                db=db_session,
                scene_id=scene.scene_id,
                image_style_id="STARK_BLACK_WHITE_NOIR",
                gemini=None,
            )
            
            # Verify artifact was created
            assert artifact is not None
            assert artifact.type == ARTIFACT_ART_DIRECTION
            assert artifact.scene_id == scene.scene_id
            
            # Verify payload structure
            payload = artifact.payload
            assert isinstance(payload, dict)
            assert "lighting" in payload
            assert "color_temperature" in payload
            assert "atmosphere_keywords" in payload
            assert "compatible_with_style" in payload
            assert "image_style_id" in payload
            
            # Verify monochrome handling
            assert payload["color_temperature"] == "N/A (monochrome)"
            assert payload["image_style_id"] == "STARK_BLACK_WHITE_NOIR"
    
    def test_art_director_artifact_retrievable(self):
        """Test that Art Director artifact can be retrieved by ArtifactService."""
        from app.db.models import Scene, Story, Project
        
        SessionLocal = get_sessionmaker()
        with SessionLocal() as db_session:
            # Create test data
            project = Project(name="Test Project")
            db_session.add(project)
            db_session.flush()
            
            story = Story(
                project_id=project.project_id,
                title="Test Story",
            )
            db_session.add(story)
            db_session.flush()
            
            scene = Scene(
                story_id=story.story_id,
                source_text="A romantic sunset scene.",
            )
            db_session.add(scene)
            db_session.flush()
            
            # Run Art Director
            artifact = run_art_director(
                db=db_session,
                scene_id=scene.scene_id,
                image_style_id="SOFT_ROMANTIC_WEBTOON",
                gemini=None,
            )
            
            # Retrieve artifact using ArtifactService
            svc = ArtifactService(db_session)
            retrieved = svc.get_latest_artifact(scene.scene_id, ARTIFACT_ART_DIRECTION)
            
            assert retrieved is not None
            assert retrieved.artifact_id == artifact.artifact_id
            assert retrieved.type == ARTIFACT_ART_DIRECTION
            assert retrieved.payload["image_style_id"] == "SOFT_ROMANTIC_WEBTOON"
    
    def test_art_director_respects_planning_lock(self):
        """Test that Art Director reuses existing artifact when planning is locked."""
        from app.db.models import Scene, Story, Project
        
        SessionLocal = get_sessionmaker()
        with SessionLocal() as db_session:
            # Create test data
            project = Project(name="Test Project")
            db_session.add(project)
            db_session.flush()
            
            story = Story(
                project_id=project.project_id,
                title="Test Story",
            )
            db_session.add(story)
            db_session.flush()
            
            scene = Scene(
                story_id=story.story_id,
                source_text="A dramatic action scene.",
                planning_locked=False,
            )
            db_session.add(scene)
            db_session.flush()
            
            # Run Art Director first time
            artifact1 = run_art_director(
                db=db_session,
                scene_id=scene.scene_id,
                image_style_id="CINEMATIC_MODERN_MANHWA",
                gemini=None,
            )
            
            # Lock planning
            scene.planning_locked = True
            db_session.commit()
            
            # Run Art Director second time
            artifact2 = run_art_director(
                db=db_session,
                scene_id=scene.scene_id,
                image_style_id="CINEMATIC_MODERN_MANHWA",
                gemini=None,
            )
            
            # Should reuse the same artifact
            assert artifact2.artifact_id == artifact1.artifact_id
    
    def test_art_director_with_different_styles(self):
        """Test that Art Director handles different image styles correctly."""
        from app.db.models import Scene, Story, Project
        
        SessionLocal = get_sessionmaker()
        with SessionLocal() as db_session:
            # Create test data
            project = Project(name="Test Project")
            db_session.add(project)
            db_session.flush()
            
            story = Story(
                project_id=project.project_id,
                title="Test Story",
            )
            db_session.add(story)
            db_session.flush()
            
            # Test monochrome style
            scene1 = Scene(
                story_id=story.story_id,
                source_text="A noir detective scene.",
            )
            db_session.add(scene1)
            db_session.flush()
            
            artifact1 = run_art_director(
                db=db_session,
                scene_id=scene1.scene_id,
                image_style_id="STARK_BLACK_WHITE_NOIR",
                gemini=None,
            )
            
            assert artifact1.payload["color_temperature"] == "N/A (monochrome)"
            
            # Test color style
            scene2 = Scene(
                story_id=story.story_id,
                source_text="A vibrant fantasy scene.",
            )
            db_session.add(scene2)
            db_session.flush()
            
            artifact2 = run_art_director(
                db=db_session,
                scene_id=scene2.scene_id,
                image_style_id="VIBRANT_FANTASY_WEBTOON",
                gemini=None,
            )
            
            assert artifact2.payload["color_temperature"] == "neutral"
            assert artifact2.payload["color_temperature"] != "N/A (monochrome)"
