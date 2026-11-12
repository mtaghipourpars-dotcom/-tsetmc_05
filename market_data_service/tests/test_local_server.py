from pathlib import Path
import shutil
import asyncio
import pytest
from sqlalchemy import select, func, text
from src.local_server import prepare, instance_lock
from src.repositories.models import TABLES, raw_responses


def test_native_migrates_and_preserves_data_and_token(tmp_path):
    project = tmp_path / 'market_data_service'
    project.mkdir()
    data = tmp_path / 'Data'
    data.mkdir()
    shutil.copy(Path(__file__).resolve().parents[2] / 'Data' / 'Ayar.md', data)
    settings, db, needs_queue = prepare(project)
    token = settings.admin_token.get_secret_value()
    assert len(token) >= 32
    assert needs_queue
    with db.connect() as conn:
        count = conn.scalar(select(func.count()).select_from(TABLES['price_history']))
        raw_count = conn.scalar(select(func.count()).select_from(raw_responses))
        assert conn.scalar(text('select version_num from alembic_version')) == '0003'
        assert conn.scalar(text('PRAGMA journal_mode')) == 'wal'
    assert count > 100
    db.dispose()
    settings2, db2, _ = prepare(project)
    assert settings2.admin_token.get_secret_value() == token
    with db2.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(TABLES['price_history'])) == count
        assert conn.scalar(select(func.count()).select_from(raw_responses)) == raw_count
    db2.dispose()


def test_native_single_instance_lock(tmp_path):
    path = tmp_path / 'lock'
    with instance_lock(path):
        with pytest.raises(RuntimeError, match='already running'):
            with instance_lock(path):
                pass
    with instance_lock(path):
        pass


@pytest.mark.asyncio
async def test_native_collector_lifecycle(engine, settings, monkeypatch):
    from src.web.app import create_app
    from src.services.collection import Collections
    called = asyncio.Event()
    async def process_one(self):
        called.set()
        return False
    monkeypatch.setattr(Collections, 'process_one', process_one)
    app = create_app(settings=settings, engine=engine, background=True)
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(called.wait(), 3)
