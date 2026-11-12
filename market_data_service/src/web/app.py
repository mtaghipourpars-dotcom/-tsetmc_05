from contextlib import asynccontextmanager
import os
from decimal import Decimal
from secrets import compare_digest
from typing import Annotated, Literal, Any
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text, func
from src.api.client import BrsClient, UpstreamError
from src.api.endpoints import ENDPOINTS, validate_params
from src.config.settings import Settings
from src.config.logging import configure
from src.repositories.database import engine_for, page
from src.repositories.models import symbols, indices, TABLES, sync_runs, sync_errors, raw_responses
from src.services.sync import SyncService
from src.services.normalization import symbol, jalali_date
from src.services.locking import operation_lock, BusyError


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    all_pages: bool = False


def create_app(settings=None, engine=None, client=None, tse_client=None, background=False):
    settings = settings or Settings(_env_file=os.environ.get('DIDBAN_ENV_FILE', '.env'))
    engine = engine or engine_for(settings.database_url)
    client = client or BrsClient(settings)
    service = SyncService(engine, client)
    from src.api.tsetmc import TseClient, CATALOG
    from src.services.tsetmc_sync import TseSync
    from src.repositories.models import provider_requests, market_observations
    tse_client = tse_client or TseClient(settings)
    tse_service = TseSync(engine, tse_client)

    @asynccontextmanager
    async def lifespan(app):
        configure(settings.log_path)
        worker = scheduler = None
        if background:
            import asyncio
            import logging
            from src.scheduler.jobs import Jobs, build_scheduler
            from src.scheduler.tsetmc_jobs import TseJobs
            async def collect():
                while True:
                    try:
                        worked = await queue.process_one()
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logging.getLogger('market').error('collector_iteration_failed')
                        worked = False
                    await asyncio.sleep(0 if worked else 2)
            worker = asyncio.create_task(collect())
            jobs = TseJobs(tse_service, service) if settings.data_provider == 'tsetmc' else Jobs(service)
            scheduler = build_scheduler(jobs)
            scheduler.start()
        try:
            yield
        finally:
            if scheduler:
                scheduler.shutdown(wait=False)
            if worker:
                import asyncio
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
            await client.close()
            await tse_client.close()
            engine.dispose()

    app = FastAPI(title='Iran Market Data API', version='3.0.0', lifespan=lifespan,
                  description='Read stored BrsApi data. Monetary values are serialized as decimal strings. No upstream calls on GET.')
    app.state.engine = engine

    def authorized(token, expected):
        return bool(expected) and bool(token) and compare_digest(token, expected)

    def read_auth(x_api_token: Annotated[str | None, Header()] = None):
        expected = settings.read_token.get_secret_value()
        if expected and not authorized(x_api_token, expected):
            raise HTTPException(401, 'Invalid read token')

    def admin_auth(x_admin_token: Annotated[str | None, Header()] = None):
        if not authorized(x_admin_token, settings.admin_token.get_secret_value()):
            raise HTTPException(401, 'Configure and provide X-Admin-Token')

    def response(value):
        return jsonable_encoder(value, custom_encoder={Decimal: str})

    def date_condition(table, start, end):
        try:
            start = jalali_date(start) if start else None
            end = jalali_date(end) if end else None
        except ValueError:
            raise HTTPException(422, 'Invalid date') from None
        if start and end and start > end:
            raise HTTPException(422, 'Invalid date range')
        return ([table.c.date_shamsi >= start] if start else []) + ([table.c.date_shamsi <= end] if end else [])

    def fetch_dataset(dataset, l18=None, start=None, end=None, limit=100, offset=0, extra=()):
        table = TABLES[dataset]
        conditions = date_condition(table, start, end) + list(extra)
        with engine.connect() as conn:
            if l18:
                sid = conn.execute(select(symbols.c.id).where(symbols.c.symbol_l18 == symbol(l18))).scalar_one_or_none()
                if sid is None:
                    raise HTTPException(404, 'Symbol not found')
                conditions.append(table.c.symbol_id == sid)
            return response(page(conn, table, conditions, limit, offset))

    @app.get('/', include_in_schema=False)
    def root():
        return FileResponse(Path(__file__).with_name('static') / 'index.html')

    @app.get('/health')
    def health():
        try:
            with engine.connect() as conn:
                conn.execute(select(symbols.c.id).limit(1))
            return {'status': 'ok'}
        except Exception:
            raise HTTPException(503, 'Database unavailable') from None

    @app.get('/api/symbols', dependencies=[Depends(read_auth)])
    def list_symbols(q: str = '', limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        with engine.connect() as conn:
            conditions = [symbols.c.symbol_l18.contains(symbol(q), autoescape=True)] if q else []
            return response(page(conn, symbols, conditions, limit, offset))

    @app.get('/api/symbols/{l18}/history', dependencies=[Depends(read_auth)])
    def history(l18: str, type: Literal['price', 'client'] = 'price', start: str | None = None, end: str | None = None,
                limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return fetch_dataset('price_history' if type == 'price' else 'client_type_history', l18, start, end, limit, offset)

    @app.get('/api/symbols/{l18}/candlesticks', dependencies=[Depends(read_auth)])
    def candles(l18: str, type: Literal['intraday', 'unadjusted', 'adjusted'] = 'adjusted', start: str | None = None,
                end: str | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        kind = {'intraday': 1, 'unadjusted': 2, 'adjusted': 3}[type]
        return fetch_dataset('candlesticks', l18, start, end, limit, offset, [TABLES['candlesticks'].c.candle_type == kind])

    @app.get('/api/indices', dependencies=[Depends(read_auth)])
    def index_values(type: int = Query(1, ge=1, le=3), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        with engine.connect() as conn:
            ids = select(indices.c.id).where(indices.c.index_type == type)
            return response(page(conn, TABLES['index_values'], [TABLES['index_values'].c.index_id.in_(ids)], limit, offset))

    @app.get('/api/codal/announcements', dependencies=[Depends(read_auth)])
    def announcements(l18: str | None = None, start: str | None = None, end: str | None = None,
                      limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return fetch_dataset('codal_announcements', l18, start, end, limit, offset)

    @app.get('/api/data/{dataset}', dependencies=[Depends(read_auth)])
    def data(dataset: str, l18: str | None = None, start: str | None = None, end: str | None = None,
             limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), include_canceled: bool = False):
        if dataset not in TABLES:
            raise HTTPException(404, 'Unknown dataset')
        extra = [TABLES['transactions'].c.canceled.is_(False)] if dataset == 'transactions' and not include_canceled else []
        return fetch_dataset(dataset, l18, start, end, limit, offset, extra)

    @app.get('/api/endpoints', dependencies=[Depends(read_auth)])
    def endpoints():
        return {k: {'path': v.path, 'required': v.required, 'optional': v.optional, 'types': v.types} for k, v in ENDPOINTS.items()}

    @app.get('/api/admin/status', dependencies=[Depends(admin_auth)])
    def status():
        with engine.connect() as conn:
            return response({'runs': page(conn, sync_runs, limit=20), 'errors': page(conn, sync_errors, limit=20)})

    @app.post('/api/admin/sync', dependencies=[Depends(admin_auth)])
    async def sync(body: SyncRequest):
        try:
            params = dict(body.params)
            validate_params(body.endpoint, params)
            if body.endpoint == 'transactions' and not params.get('date'):
                raise ValueError('Transactions require explicit date to prevent false dating')
            with operation_lock(engine):
                if body.all_pages:
                    if body.endpoint != 'codal':
                        raise ValueError('all_pages only applies to codal')
                    return await service.codal_pages(**params)
                return await service.sync(body.endpoint, **params)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        except BusyError:
            raise HTTPException(409, 'Another sync is running') from None
        except UpstreamError as e:
            raise HTTPException(502, {'kind': e.kind, 'upstream_status': e.status}) from None

    class TseRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        endpoint: str
        path_params: dict[str, str | int] = Field(default_factory=dict)
        query: dict[str, str | int | bool] = Field(default_factory=dict)

    @app.get('/api/tsetmc/catalog', dependencies=[Depends(read_auth)])
    def tse_catalog():
        return {'source': 'TSETMC/TSE public read-only endpoints', 'count': len(CATALOG), 'items': list(CATALOG.values())}

    @app.post('/api/admin/tsetmc/sync', dependencies=[Depends(admin_auth)])
    async def tse_sync(body: TseRequest):
        try:
            with operation_lock(engine):
                return await tse_service.sync(body.endpoint, body.path_params, body.query)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        except BusyError:
            raise HTTPException(409, 'Another sync is running') from None
        except UpstreamError as e:
            raise HTTPException(502, {'kind': e.kind, 'upstream_status': e.status}) from None

    @app.get('/api/tsetmc/requests', dependencies=[Depends(read_auth)])
    def tse_requests(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        with engine.connect() as conn:
            result = page(conn, provider_requests, limit=limit, offset=offset)
            for item in result['items']:
                item.pop('payload', None)
            return response(result)

    @app.get('/api/tsetmc/requests/{request_id}', dependencies=[Depends(read_auth)])
    def tse_payload(request_id: int):
        with engine.connect() as conn:
            row = conn.execute(select(provider_requests).where(provider_requests.c.id == request_id)).mappings().first()
            if row is None:
                raise HTTPException(404, 'Request not found')
            return response(dict(row))

    @app.get('/api/tsetmc/observations', dependencies=[Depends(read_auth)])
    def observations(endpoint: str | None = None, instrument_code: str | None = None,
                     limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        conditions=[]
        if endpoint: conditions.append(market_observations.c.endpoint == endpoint)
        if instrument_code: conditions.append(market_observations.c.instrument_code == instrument_code)
        with engine.connect() as conn:
            return response(page(conn, market_observations, conditions, limit, offset))

    from src.services.collection import Collections
    from src.web.dashboard import router_for
    queue = Collections(engine, tse_service, service)
    app.state.collections = queue
    app.include_router(router_for(engine, queue, read_auth, admin_auth, settings))
    app.mount('/static', StaticFiles(directory=Path(__file__).with_name('static')), name='static')
    return app


app = create_app()
