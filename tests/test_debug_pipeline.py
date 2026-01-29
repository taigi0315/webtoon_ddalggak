import json
from app.graphs.pipeline import run_full_pipeline
from app.db.models import Project, Story, Scene
from app.db.session import get_sessionmaker
from app.graphs import nodes


class FakeGemini:
    def generate_text(self, prompt: str, model=None) -> str:
        return '{}'

    def generate_image(self, prompt: str, model=None):
        return b'fake', 'image/png'


def test_run_full_pipeline_smoke():
    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        project = Project(name='p')
        db.add(project)
        db.commit()
        db.refresh(project)
        story = Story(project_id=project.project_id, title='s')
        db.add(story)
        db.commit()
        db.refresh(story)
        scene = Scene(story_id=story.story_id, source_text='hello')
        db.add(scene)
        db.commit()
        db.refresh(scene)

        class TestFakeGemini:
            def generate_text(self, prompt: str, model=None) -> str:
                if "Extract scene intent" in prompt:
                    return '{}'
                if "Generate a panel plan" in prompt:
                    return json.dumps({"panels": [{"grammar_id": "establishing"}, {"grammar_id": "reaction"}, {"grammar_id": "dialogue_medium"}]})
                if "Fill panel semantics" in prompt:
                    return json.dumps({"panels": [{"grammar_id": "establishing", "text": "wide street"}, {"grammar_id": "reaction", "text": "shock"}, {"grammar_id": "dialogue_medium", "text": "talking"}]})
                return json.dumps({})

            def generate_image(self, prompt: str, model=None):
                return b'fake', 'image/png'

        gem = TestFakeGemini()

        # Run individual nodes to inspect intermediate artifacts
        si = nodes.run_scene_intent_extractor(db=db, scene_id=scene.scene_id, gemini=gem)
        pp = nodes.run_panel_plan_generator(db=db, scene_id=scene.scene_id, panel_count=3, gemini=gem)
        print('PP PAYLOAD', pp.payload)
        ppn = nodes.run_panel_plan_normalizer(db=db, scene_id=scene.scene_id)
        print('PPN PAYLOAD', ppn.payload)
        lt = nodes.run_layout_template_resolver(db=db, scene_id=scene.scene_id)
        print('LT PAYLOAD', lt.payload)
        ps = nodes.run_panel_semantic_filler(db=db, scene_id=scene.scene_id, gemini=gem)
        print('PS PAYLOAD', ps.payload)

        assert pp.payload.get('panels')
        assert ppn.payload.get('panels')
        assert lt.payload.get('panels')
        assert ps.payload.get('panels')
        
        out = run_full_pipeline(db=db, scene_id=scene.scene_id, panel_count=3, style_id='default', gemini=FakeGemini())
        assert 'panel_plan_artifact_id' in out
