"""Single-process localhost runtime: SQLite, API, collector and scheduler."""
import argparse
import os
from pathlib import Path
import secrets
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def instance_lock(path):
    """OS lock released even after a crash; shared by Windows and Unix launchers."""
    with path.open('a+b') as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Didban is already running. Use its existing window.') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def prepare(directory=ROOT):
    from alembic import command
    from alembic.config import Config
    from src.config.settings import Settings
    from src.repositories.database import engine_for
    from src.repositories.models import symbols, collection_jobs
    from src.services.import_repository import import_history
    from sqlalchemy import select
    directory = Path(directory).resolve()
    data_dir = directory / 'local_data'
    data_dir.mkdir(exist_ok=True)
    env_path = directory / '.env.local'
    if not env_path.exists():
        env_path.write_text('ADMIN_TOKEN=' + secrets.token_urlsafe(32) + '\n'
                            'DATA_PROVIDER=tsetmc\nBRS_API_KEY=\n'
                            'BRS_FALLBACK_ENABLED=false\nSELECTED_SYMBOLS=\n', encoding='utf-8')
        env_path.chmod(0o600)
    url = 'sqlite:///' + (data_dir / 'didban.db').as_posix()
    settings = Settings(_env_file=env_path, database_url=url, log_path=str(data_dir / 'market.jsonl'))
    if not settings.admin_token.get_secret_value():
        raise RuntimeError('Set ADMIN_TOKEN in .env.local before starting.')
    cfg = Config(str(ROOT / 'alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT / 'migrations'))
    cfg.attributes['database_url'] = url
    command.upgrade(cfg, 'head')
    engine = engine_for(url)
    with engine.connect() as conn:
        empty = conn.execute(select(symbols.c.id).limit(1)).first() is None
    if empty:
        source = directory.parent / 'Data'
        if source.is_dir():
            report = import_history(engine, source)
            print('Imported historical records:', sum(r['accepted'] for r in report), flush=True)
    with engine.connect() as conn:
        needs_queue = conn.execute(select(collection_jobs.c.id).limit(1)).first() is None
    return settings, engine, needs_queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    (ROOT / 'local_data').mkdir(exist_ok=True)
    with instance_lock(ROOT / 'local_data' / 'server.lock'):
        settings, engine, needs_queue = prepare()
        # The ASGI compatibility app also reads Settings at module import time.
        os.environ['DATABASE_URL'] = settings.database_url
        os.environ['DIDBAN_ENV_FILE'] = str(ROOT / '.env.local')
        from src.web.app import create_app
        app = create_app(settings=settings, engine=engine, background=True)
        if needs_queue:
            app.state.collections.create(source='tsetmc', scope='all')
        print('Open http://127.0.0.1:%d | Stop: Ctrl+C' % args.port, flush=True)
        print('Management token: market_data_service/.env.local (ADMIN_TOKEN)', flush=True)
        if not args.no_browser:
            import threading
            import webbrowser
            timer = threading.Timer(2, webbrowser.open, args=(f'http://127.0.0.1:{args.port}',))
            timer.daemon = True
            timer.start()
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, workers=1)


if __name__ == '__main__':
    main()
