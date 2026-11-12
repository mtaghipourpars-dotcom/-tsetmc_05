import argparse
import asyncio
import json
from src.config.settings import Settings
from src.config.logging import configure
from src.repositories.database import engine_for
from src.api.client import BrsClient, UpstreamError
from src.services.sync import SyncService
from src.services.locking import operation_lock, BusyError
from src.scheduler.jobs import Jobs


async def run(args):
    settings = Settings()
    configure(settings.log_path)
    engine = engine_for(settings.database_url)
    client = BrsClient(settings)
    service = SyncService(engine, client)
    try:
        if args.command == 'initialize-webapp':
            from src.services.import_repository import import_history
            from src.repositories.models import collection_jobs
            from sqlalchemy import select,func
            print(json.dumps(import_history(engine,args.directory),ensure_ascii=False))
            with engine.connect() as conn:
                existing=conn.execute(select(func.count()).select_from(collection_jobs)).scalar_one()
            if not existing:
                from src.services.collection import Collections
                print(json.dumps({'collection_id':Collections(engine,None,None).create('tsetmc','all')}))
        elif args.command == 'import-repository':
            from src.services.import_repository import import_history
            print(json.dumps(import_history(engine,args.directory),ensure_ascii=False,indent=2))
        elif args.command == 'phase':
            if settings.data_provider == 'tsetmc':
                from src.api.tsetmc import TseClient
                from src.services.tsetmc_sync import TseSync
                from src.scheduler.tsetmc_jobs import TseJobs
                tse=TseClient(settings)
                try:
                    await TseJobs(TseSync(engine,tse),service).run(args.phase)
                finally:
                    await tse.close()
            else:
                await Jobs(service).run(args.phase)
        elif args.command == 'tsetmc':
            from src.api.tsetmc import TseClient
            from src.services.tsetmc_sync import TseSync
            tse=TseClient(settings)
            try:
                with operation_lock(engine):
                    print(json.dumps(await TseSync(engine,tse).sync(args.endpoint,json.loads(args.path_params),json.loads(args.query)),ensure_ascii=False))
            finally:
                await tse.close()
        elif args.command == 'sync':
            params = json.loads(args.params)
            if args.endpoint == 'transactions' and not params.get('date'):
                raise ValueError('Transactions require explicit date')
            with operation_lock(engine):
                print(json.dumps(await service.sync(args.endpoint, **params), ensure_ascii=False))
        elif args.command == 'verify-live':
            # Explicit operator invocation; a finite set of calls, no scheduler.
            calls = [('symbols', {'type': 1}), ('indices', {'type': 1}), ('symbol', {'l18': args.symbol}),
                ('nav', {'l18': args.fund}), ('options', {}), ('transactions', {'l18': args.symbol, 'date': args.date}),
                ('history', {'l18': args.symbol, 'type': 0}), ('history', {'l18': args.symbol, 'type': 1}),
                *[('candles', {'l18': args.symbol, 'type': t}) for t in (1, 2, 3)],
                ('shareholders', {'l18': args.symbol, 'date': args.date}), ('codal', {'l18': args.symbol, 'page': 1}),
                *[(x, {}) for x in ('ime_futures', 'ime_options', 'ime_certificates', 'ime_funds', 'commodities')],
                ('ime_physical', {'date_start': args.date, 'date_end': args.date})]
            results = []
            with operation_lock(engine):
                for endpoint, params in calls:
                    try:
                        results.append({'endpoint': endpoint, 'result': await service.sync(endpoint, **params)})
                    except UpstreamError as e:
                        results.append({'endpoint': endpoint, 'error': e.kind, 'status': e.status})
                        if e.status == 429 or e.kind in ('network', 'missing_key', 'api_error'):
                            break
            print(json.dumps(results, ensure_ascii=False, indent=2))
    finally:
        await client.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    initialize = sub.add_parser('initialize-webapp')
    initialize.add_argument('directory')
    imp = sub.add_parser('import-repository')
    imp.add_argument('directory')
    phase = sub.add_parser('phase')
    phase.add_argument('phase', choices=['bootstrap', 'intraday', 'daily', 'weekly'])
    sync = sub.add_parser('sync')
    sync.add_argument('endpoint')
    sync.add_argument('--params', default='{}')
    tse = sub.add_parser('tsetmc')
    tse.add_argument('endpoint')
    tse.add_argument('--path-params', default='{}')
    tse.add_argument('--query', default='{}')
    live = sub.add_parser('verify-live')
    live.add_argument('--symbol', default='فملی')
    live.add_argument('--fund', default='اهرم')
    live.add_argument('--date', required=True)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except (UpstreamError, BusyError, ValueError) as e:
        parser.exit(1, f'{e}\n')


if __name__ == '__main__':
    main()
