import asyncio
import logging
from sqlalchemy import select
from src.api.client import UpstreamError
from src.repositories.models import symbols
from src.services.normalization import jalali_date, today
from src.services.locking import operation_lock, BusyError


class Jobs:
    def __init__(self, service):
        self.service = service
        self.settings = service.client.settings

    def selected(self):
        selected = self.settings.symbols()
        if selected:
            return selected
        with self.service.engine.connect() as conn:
            return list(conn.execute(select(symbols.c.symbol_l18).where(symbols.c.is_active.is_(True)).order_by(symbols.c.id)).scalars())

    async def safe(self, endpoint, **params):
        try:
            return await self.service.sync(endpoint, **params)
        except UpstreamError as e:
            logging.getLogger('market').warning('sync_failed endpoint=%s kind=%s', endpoint, e.kind)
            if e.status in (401, 403, 429) or e.kind in ('missing_key', 'api_error', 'network'):
                raise  # stop a broken/quota-exhausted batch
            return None

    async def run(self, phase):
        with operation_lock(self.service.engine):
            if phase in ('bootstrap', 'daily'):
                for market_type in map(int, self.settings.market_types.split(',')):
                    await self.safe('symbols', type=market_type)
            if phase == 'bootstrap':
                return
            selected = self.selected()
            if phase == 'intraday':
                for index_type in (1, 2, 3):
                    await self.safe('indices', type=index_type)
                for name in selected:
                    await self.safe('symbol', l18=name)
                    await self.safe('candles', l18=name, type=1)
            elif phase == 'daily':
                for name in selected:
                    for kind in (0, 1):
                        await self.safe('history', l18=name, type=kind)
                    for kind in (2, 3):
                        await self.safe('candles', l18=name, type=kind)
                    # Explicit last-trade date from provider; never assume today's date.
                    result = await self.safe('symbol', l18=name)
                    if result:
                        from src.repositories.models import raw_responses
                        with self.service.engine.connect() as conn:
                            payload = conn.execute(select(raw_responses.c.payload).where(raw_responses.c.id == result['raw_id'])).scalar_one()
                        from src.services.normalization import records
                        rows = records(payload)
                        if rows and rows[0].get('date_update'):
                            d = jalali_date(rows[0]['date_update'])
                            await self.safe('transactions', l18=name, date=d)
                    await self.safe('shareholders', l18=name)
            elif phase == 'weekly':
                for name in self.settings.nav_symbols.split(','):
                    if name.strip():
                        await self.safe('nav', l18=name.strip())
                for endpoint in ('options', 'ime_futures', 'ime_options', 'ime_certificates', 'ime_funds', 'commodities'):
                    await self.safe(endpoint)
                # Physical defaults to today upstream. Explicit rolling seven-day range.
                import jdatetime
                from datetime import timedelta
                start = (jdatetime.date.fromisoformat(today()) - timedelta(days=7)).isoformat()
                await self.safe('ime_physical', date_start=start, date_end=today())
                result = await self.service.codal_pages(date_start=start, date_end=today())
                if result['status'] != 'complete':
                    logging.getLogger('market').warning('codal_truncated next_page=%s', result['next_page'])
            else:
                raise ValueError('Unknown phase')


def build_scheduler(jobs):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler(timezone='Asia/Tehran', job_defaults={'max_instances': 1, 'coalesce': True, 'misfire_grace_time': 300})
    async def guarded(phase):
        try:
            await jobs.run(phase)
        except BusyError:
            logging.getLogger('market').info('job_skipped_busy phase=%s', phase)
        except UpstreamError as e:
            logging.getLogger('market').error('job_stopped phase=%s kind=%s', phase, e.kind)
        except Exception:
            logging.getLogger('market').error('job_failed phase=%s kind=internal', phase)
    # All weekdays intentionally: different instruments have different sessions.
    # Repeated provider timestamps are idempotent. Holidays may return stale/empty data.
    scheduler.add_job(guarded, 'cron', hour='8-18', minute='*/2', args=['intraday'], id='intraday')
    scheduler.add_job(guarded, 'cron', hour=18, minute=5, args=['daily'], id='daily')
    scheduler.add_job(guarded, 'cron', day_of_week='fri', hour=18, minute=30, args=['weekly'], id='weekly')
    return scheduler
