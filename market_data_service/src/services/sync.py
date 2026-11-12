import logging
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from src.api.client import BrsClient, UpstreamError
from src.api.endpoints import validate_params
from src.repositories.models import raw_responses, sync_runs, sync_errors, now
from src.services.normalization import records
from src.services.mapper import map_rows


class SyncService:
    def __init__(self, engine, client: BrsClient):
        self.engine, self.client = engine, client

    async def sync(self, endpoint, **params):
        validate_params(endpoint, dict(params))
        with self.engine.begin() as conn:
            run_id = conn.execute(sync_runs.insert().values(endpoint=endpoint, params=params, status='running').returning(sync_runs.c.id)).scalar_one()
        try:
            return await self._execute(run_id, endpoint, params)
        except SQLAlchemyError:
            try:
                self.fail(run_id, endpoint, 'database')
            except SQLAlchemyError:
                logging.getLogger('market').error('database_unavailable run=%s', run_id)
            raise UpstreamError('database') from None

    async def _execute(self, run_id, endpoint, params):
        try:
            payload = await self.client.get(endpoint, **params)
        except UpstreamError as e:
            self.fail(run_id, endpoint, e.kind)
            raise
        # Archive independently; even malformed envelopes remain inspectable.
        with self.engine.begin() as conn:
            raw_id = conn.execute(raw_responses.insert().values(endpoint=endpoint, params=params, payload=payload).returning(raw_responses.c.id)).scalar_one()
        try:
            rows = records(payload)
        except ValueError:
            with self.engine.begin() as conn:
                conn.execute(sync_errors.insert().values(run_id=run_id, raw_id=raw_id, endpoint=endpoint, error_kind='unknown_response_shape'))
            self.fail(run_id, endpoint, 'unknown_response_shape')
            raise UpstreamError('unknown_response_shape') from None
        if endpoint == 'candles' and params.get('type') == 1 and any(isinstance(row, dict) and not row.get('date') for row in rows):
            # Official candle_intraday rows contain no date. Resolve a provider date,
            # never label a holiday's stale candles with today's calendar date.
            try:
                context = await self.sync('symbol', l18=params['l18'])
                with self.engine.connect() as conn:
                    source = conn.execute(select(raw_responses.c.payload).where(raw_responses.c.id == context['raw_id'])).scalar_one()
                source_rows = records(source)
                date = source_rows[0].get('date_update') if source_rows else None
                if not date:
                    raise ValueError('missing_date_context')
                rows = [dict(row, _context_date=date, _context_raw_id=context['raw_id']) if isinstance(row, dict) and not row.get('date') else row for row in rows]
            except (ValueError, UpstreamError, TypeError):
                self.fail(run_id, endpoint, 'missing_date_context')
                raise UpstreamError('missing_date_context') from None
        accepted = rejected = 0
        with self.engine.begin() as conn:
            for row in rows:
                try:
                    with conn.begin_nested():
                        accepted += map_rows(conn, endpoint, row, params, raw_id)
                except (ValueError, TypeError, OverflowError, DataError, IntegrityError):
                    rejected += 1
                    conn.execute(sync_errors.insert().values(run_id=run_id, raw_id=raw_id, endpoint=endpoint,
                        error_kind='invalid_record', raw=row))
            conn.execute(sync_runs.update().where(sync_runs.c.id == run_id).values(
                status='partial' if rejected else 'success', accepted=accepted, rejected=rejected, finished_at=now()))
        result = {'run_id': run_id, 'raw_id': raw_id, 'accepted': accepted, 'rejected': rejected,
                  'status': 'partial' if rejected else 'success'}
        if endpoint == 'codal' and isinstance(payload, dict):
            result['count_page'] = int(payload.get('count_page') or 1)
        logging.getLogger('market').info('sync_complete endpoint=%s run=%s accepted=%s rejected=%s', endpoint, run_id, accepted, rejected)
        return result

    def fail(self, run_id, endpoint, kind):
        with self.engine.begin() as conn:
            conn.execute(sync_runs.update().where(sync_runs.c.id == run_id).values(status='failed', error_kind=kind, finished_at=now()))
            conn.execute(sync_errors.insert().values(run_id=run_id, endpoint=endpoint, error_kind=kind))

    async def codal_pages(self, **params):
        first = int(params.pop('page', 1))
        results = []
        for page in range(first, first + self.client.settings.codal_max_pages):
            result = await self.sync('codal', page=page, **params)
            results.append(result)
            if page >= result['count_page']:
                return {'status': 'complete', 'pages': results}
        return {'status': 'truncated', 'pages': results, 'next_page': page + 1}
