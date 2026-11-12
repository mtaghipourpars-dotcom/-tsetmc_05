import logging
from sqlalchemy import select
from src.repositories.models import symbols
from src.services.locking import operation_lock
from src.api.client import UpstreamError
from src.services.normalization import symbol


class TseJobs:
    def __init__(self,service,fallback=None):
        self.service,self.fallback=service,fallback
        self.settings=service.client.settings

    async def call(self,endpoint,path=None,query=None):
        try:
            return await self.service.sync(endpoint,path,query)
        except UpstreamError as e:
            logging.getLogger('market').warning('provider_failed source=tsetmc endpoint=%s kind=%s',endpoint,e.kind)
            raise

    async def resolve(self,name):
        with self.service.engine.connect() as conn:
            code=conn.execute(select(symbols.c.ins_code).where(symbols.c.symbol_l18==symbol(name))).scalar_one_or_none()
        if not code:
            await self.call('instrument_search',{'Query':name})
            with self.service.engine.connect() as conn:
                code=conn.execute(select(symbols.c.ins_code).where(symbols.c.symbol_l18==symbol(name))).scalar_one_or_none()
        if not code:raise UpstreamError('instrument_not_found')
        return code

    async def run(self,phase):
        with operation_lock(self.service.engine):
            if phase in ('bootstrap','intraday'):
                try:
                    await self.call('market_watch')
                    await self.call('client_all')
                    await self.call('indices')
                except UpstreamError:
                    if self.settings.brs_fallback_enabled and self.fallback:
                        for endpoint,params in [('symbols',{'type':1}),('indices',{'type':1})]:
                            await self.fallback.sync(endpoint,**params)
                    else:raise
            if phase in ('bootstrap','daily'):
                names=self.settings.symbols()
                if not names:
                    with self.service.engine.connect() as conn:
                        names=list(conn.execute(select(symbols.c.symbol_l18).where(symbols.c.is_active.is_(True))).scalars())
                for name in names:
                    try:
                        code=await self.resolve(name)
                        await self.call('instrument_info',{'InsCode':code})
                        await self.call('price_history',{'InsCode':code})
                        await self.call('price_adjustments',{'InsCode':code})
                    except UpstreamError:
                        if self.settings.brs_fallback_enabled and self.fallback:
                            await self.fallback.sync('history',l18=name,type=0)
                        else:raise
            if phase=='weekly':
                # All catalog endpoints are available on demand; weekly tasks target
                # bounded public collections, not placeholder instrument ids.
                for entry in ('market_watch','client_all','indices'):
                    await self.call(entry)
            if phase not in ('bootstrap','intraday','daily','weekly'):
                raise ValueError('Unknown phase')
