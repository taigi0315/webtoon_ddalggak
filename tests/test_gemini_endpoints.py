import pytest


@pytest.mark.anyio
async def test_generate_text_endpoint_mocked(client, monkeypatch):
    from app.api.v1 import gemini as gemini_router

    def fake_build_client():
        class FakeClient:
            def generate_text(self, prompt: str, model=None):
                return f"echo:{prompt}"

        return FakeClient()

    monkeypatch.setattr(gemini_router, "_build_client", fake_build_client)

    resp = await client.post("/v1/gemini/generate-text", json={"prompt": "hi"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "echo:hi"


@pytest.mark.anyio
async def test_generate_image_endpoint_mocked(client, monkeypatch, tmp_path):
    from app.api.v1 import gemini as gemini_router
    from app.core import settings as settings_module

    settings_module.settings.media_root = str(tmp_path / "media")

    def fake_build_client():
        class FakeClient:
            def generate_image(self, prompt: str, model=None):
                return b"fakebytes", "image/png"

        return FakeClient()

    monkeypatch.setattr(gemini_router, "_build_client", fake_build_client)

    resp = await client.post("/v1/gemini/generate-image", json={"prompt": "draw a cat"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mime_type"] == "image/png"
    assert body["image_url"].startswith("/media/")
