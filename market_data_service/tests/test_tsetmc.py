import json
import pytest
import httpx
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from src.api.tsetmc import TseClient,CATALOG
from src.api.client import UpstreamError
from src.services.tsetmc_sync import TseSync
from src.repositories.models import TABLES,provider_requests,market_observations,symbols
from src.web.app import create_app


def defaults(entry):
    out={}
    for p in entry['parameters']:
        out[p]='35425587644337450' if p.lower()=='inscode' else '20261111' if p.lower()=='deven' else 'فملی' if p.lower() in ('query','symbol') else '1'
    return out


@pytest.mark.parametrize('endpoint',list(CATALOG))
async def test_every_catalog_endpoint_has_safe_executable_transport(settings,endpoint):
    entry=CATALOG[endpoint]
    calls=[]
    async def handler(r):
        calls.append(r)
        if entry['format']=='binary':return httpx.Response(200,content=b'%PDF-test',headers={'Content-Type':'application/pdf'})
        if entry['format']=='text':return httpx.Response(200,text='12/11/2026 12:00:00')
        return httpx.Response(200,json={'data':[]})
    c=TseClient(settings,transport=httpx.MockTransport(handler))
    result=await c.get(endpoint,defaults(entry))
    assert result.status==200
    assert 'test-key' not in str(calls[0].url)
    assert calls[0].url.scheme=='https'
    await c.close()


async def test_watch_query_and_official_mirror_fallback(settings):
    calls=[]
    async def handler(r):
        calls.append(r)
        if r.url.host=='cdn.tsetmc.com':return httpx.Response(503)
        return httpx.Response(200,json={'marketwatch':[]})
    settings.max_retries=0
    c=TseClient(settings,transport=httpx.MockTransport(handler))
    result=await c.get('market_watch')
    assert result.origin=='https://cdn10.tsetmc.com'
    assert calls[0].url.params['paperTypes[0]']=='1'
    assert calls[0].url.params['showTraded']=='true'
    assert len(calls)==2
    await c.close()


async def test_rate_limit_never_hops_mirrors(settings):
    calls=[]
    async def handler(r):
        calls.append(r);return httpx.Response(429,headers={'Retry-After':'60'})
    c=TseClient(settings,transport=httpx.MockTransport(handler))
    for _ in range(2):
        with pytest.raises(UpstreamError):await c.get('market_watch')
    assert len(calls)==1
    await c.close()


@pytest.mark.parametrize('path,query',[({'InsCode':'../../etc/passwd'},{}),({'InsCode':'http://bad'},{}),({'InsCode':'1'},{'key':'secret'})])
async def test_caller_cannot_inject_targets_or_credentials(settings,path,query):
    c=TseClient(settings,transport=httpx.MockTransport(lambda r:pytest.fail('must not make a request')))
    with pytest.raises(ValueError):await c.get('price_history',path,query)
    await c.close()


async def test_price_history_normalized_and_provider_archive_retained(engine,settings):
    async def handler(r):
        if 'GetInstrumentSearch' in r.url.path:
            return httpx.Response(200,json={'instrumentSearch':[{'insCode':'35425587644337450','lVal18AFC':'فملی','lVal30':'ملی مس'}]})
        return httpx.Response(200,json={'closingPriceDaily':[{'dEven':20261111,'priceFirst':0,'priceMin':90,'priceMax':110,'pClosing':100,'pDrCotVal':101,'qTotTran5J':20,'qTotCap':2000,'zTotTran':2}]})
    c=TseClient(settings,transport=httpx.MockTransport(handler));s=TseSync(engine,c)
    await s.sync('instrument_search',{'Query':'فملی'})
    for _ in range(2):await s.sync('price_history',{'InsCode':'35425587644337450'})
    with engine.connect() as conn:
        rows=conn.execute(select(TABLES['price_history'])).mappings().all()
        assert len(rows)==1 and rows[0]['source']=='tsetmc' and rows[0]['price_first']==0
        assert conn.execute(select(func.count()).select_from(provider_requests)).scalar_one()==3
        assert conn.execute(select(func.count()).select_from(market_observations)).scalar_one()==2
    await c.close()


async def test_timestamp_missing_remains_flagged_and_not_fabricated(engine,settings):
    c=TseClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'clientTypeAllDto':[{'insCode':'123','buy_I_Volume':100}]})))
    await TseSync(engine,c).sync('client_all')
    with engine.connect() as conn:
        row=conn.execute(select(market_observations)).mappings().one()
        assert row['date_shamsi'] is None and row['quality']==['source_date_missing']
    await c.close()


async def test_transport_failure_is_saved(engine,settings):
    settings.max_retries=0
    c=TseClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(503)))
    with pytest.raises(UpstreamError):await TseSync(engine,c).sync('indices')
    with engine.connect() as conn:
        row=conn.execute(select(provider_requests)).mappings().one()
        assert row['status']=='failed' and row['http_status']==503
    await c.close()


async def test_brs_blocked_account_not_retried(settings):
    from src.api.client import BrsClient
    calls=[]
    async def handler(r):
        calls.append(r);return httpx.Response(403,text='کلید وب‌سرویس شما مسدود به دلیل بیش از ظرفیت')
    c=BrsClient(settings,transport=httpx.MockTransport(handler))
    for _ in range(2):
        with pytest.raises(UpstreamError,match='account_blocked'):await c.get('symbols')
    assert len(calls)==1
    await c.close()


def test_tsetmc_web_sync_and_read(engine,settings):
    c=TseClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'indexB1':[{'lVal30':'شاخص کل','xDrNivJIdx004':100,'indexChange':1}]})))
    with TestClient(create_app(settings,engine,tse_client=c)) as web:
        assert web.get('/api/tsetmc/catalog').json()['count']==len(CATALOG)
        assert web.post('/api/admin/tsetmc/sync',json={'endpoint':'indices'}).status_code==401
        result=web.post('/api/admin/tsetmc/sync',headers={'X-Admin-Token':'admin-test'},json={'endpoint':'indices'})
        assert result.status_code==200 and result.json()['accepted']==1
        request_id=result.json()['request_id']
        assert web.get(f'/api/tsetmc/requests/{request_id}').json()['status']=='success'
        assert web.get('/api/tsetmc/observations?endpoint=indices').json()['total']==1
        assert web.get('/api/indices').json()['items'][0]['source']=='tsetmc'
