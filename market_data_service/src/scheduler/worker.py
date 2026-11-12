import asyncio
import signal
from sqlalchemy import text
from src.api.client import BrsClient
from src.config.settings import Settings
from src.config.logging import configure
from src.repositories.database import engine_for
from src.services.sync import SyncService
from src.scheduler.jobs import Jobs, build_scheduler


async def main():
    settings = Settings()
    configure(settings.log_path)
    engine = engine_for(settings.database_url)
    # Dedicated singleton scheduler lock; sync lock has a separate id.
    lock_conn = engine.connect()
    if engine.dialect.name == 'postgresql':
        acquired = lock_conn.execute(text('SELECT pg_try_advisory_lock(719304822)')).scalar()
        lock_conn.commit()
        if not acquired:
            raise RuntimeError('A scheduler is already running')
    client = BrsClient(settings)
    tse_client = None
    if settings.data_provider == 'tsetmc':
        from src.api.tsetmc import TseClient
        from src.services.tsetmc_sync import TseSync
        from src.scheduler.tsetmc_jobs import TseJobs
        tse_client = TseClient(settings)
        jobs = TseJobs(TseSync(engine, tse_client), SyncService(engine, client))
    else:
        jobs = Jobs(SyncService(engine, client))
    scheduler = build_scheduler(jobs)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    scheduler.start()
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=False)
        await client.close()
        if tse_client:
            await tse_client.close()
        lock_conn.close()
        engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
