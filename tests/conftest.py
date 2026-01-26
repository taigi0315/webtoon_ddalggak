import pytest
import httpx

from app.core import settings as settings_module
from app.db.base import Base
from app.db.session import get_engine, init_engine
from app.main import app


@pytest.fixture(autouse=True)
def _use_test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    monkeypatch.setattr(settings_module.settings, "database_url", database_url)
    monkeypatch.setattr(settings_module.settings, "db_auto_create", True)

    init_engine(database_url)
    Base.metadata.create_all(bind=get_engine())

    yield


@pytest.fixture()
async def client():
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
