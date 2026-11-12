import asyncio
import logging
import signal
from src.config.settings import Settings
from src.config.logging import configure
from src.repositories.database import engine_for
from src.api.client import BrsClient
from src.api.tsetmc import TseClient
from src.services.sync import SyncService
from src.services.tsetmc_sync import TseSync
from src.services.collection import Collections


async def main():
    settings=Settings();configure(settings.log_path)
    engine=engine_for(settings.database_url);brs=BrsClient(settings);tse=TseClient(settings)
    queue=Collections(engine,TseSync(engine,tse),SyncService(engine,brs))
    stop=asyncio.Event()
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    try:
        while not stop.is_set():
            try:worked=await queue.process_one()
            except Exception:
                logging.getLogger('market').error('collector_iteration_failed');worked=False
            if not worked:
                try:await asyncio.wait_for(stop.wait(),timeout=2)
                except asyncio.TimeoutError:pass
    finally:
        await tse.close();await brs.close();engine.dispose()


if __name__=='__main__':asyncio.run(main())
