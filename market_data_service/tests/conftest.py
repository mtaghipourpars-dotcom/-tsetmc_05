import pytest
import httpx
from src.config.settings import Settings
from src.repositories.database import engine_for
from src.repositories.models import metadata
from src.api.client import BrsClient
from src.services.sync import SyncService


@pytest.fixture
def engine():
    db = engine_for('sqlite+pysqlite:///:memory:')
    metadata.create_all(db)
    yield db
    db.dispose()


@pytest.fixture
def settings():
    return Settings(_env_file=None, brs_api_key='test-key', admin_token='admin-test', request_interval=0, max_retries=2)


def service_for(engine, settings, payload, status=200):
    async def handler(request):
        return httpx.Response(status, json=payload)
    return SyncService(engine, BrsClient(settings, transport=httpx.MockTransport(handler)))
