import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

@pytest.mark.anyio
async def test_generate_story_scenes_batch(client):
    # Setup
    project = (await client.post("/v1/projects", json={"name": "p"})).json()
    story = (
        await client.post(
            f"/v1/projects/{project['project_id']}/stories",
            json={"title": "s", "default_image_style": "default"},
        )
    ).json()
    
    # Create scenes
    await client.post(
        f"/v1/stories/{story['story_id']}/scenes",
        json={"source_text": "Scene 1"}
    )
    await client.post(
        f"/v1/stories/{story['story_id']}/scenes",
        json={"source_text": "Scene 2"}
    )
    
    # Mock enqueue_job
    with patch("app.services.job_queue.enqueue_job") as mock_enqueue:
        mock_job = MagicMock()
        mock_job.job_id = uuid4()
        mock_job.job_type = "scene_full"
        mock_job.status = "queued"
        mock_job.created_at = datetime.utcnow()
        mock_job.updated_at = datetime.utcnow()
        mock_job.progress = None
        mock_job.result = None
        mock_job.error = None
        mock_enqueue.return_value = mock_job
        
        # Call batch generation
        resp = await client.post(
            f"/v1/stories/{story['story_id']}/generate/scenes",
            json={"panel_count": 3}
        )
        
        assert resp.status_code == 202
        data = resp.json()
        assert data["story_id"] == story["story_id"]
        assert len(data["jobs"]) == 2
        assert mock_enqueue.call_count == 2
