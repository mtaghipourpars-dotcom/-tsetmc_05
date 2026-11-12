import httpx
from fastapi.testclient import TestClient
from src.api.client import BrsClient
from src.web.app import create_app
from src.scheduler.jobs import build_scheduler
from src.services.locking import operation_lock, BusyError
import pytest


def test_read_api_never_calls_upstream_and_admin_is_protected(engine, settings):
    def forbidden(r):
        pytest.fail('GET API must not call upstream')
    app=create_app(settings,engine,BrsClient(settings,transport=httpx.MockTransport(forbidden)))
    with TestClient(app) as web:
        assert web.get('/health').status_code==200
        assert web.get('/api/symbols').json()['total']==0
        assert web.get('/api/data/transactions').status_code==200
        assert web.get('/api/data/not-a-table').status_code==404
        assert web.get('/api/symbols/missing/history').status_code==404
        assert web.get('/api/data/price_history?start=1405-13-01').status_code==422
        assert web.get('/api/data/price_history?limit=1001').status_code==422
        assert web.post('/api/admin/sync',json={'endpoint':'symbols'}).status_code==401
        assert web.get('/api/admin/status').status_code==401
        assert web.get('/api/endpoints').json()['commodities']['path']=='Market/Commodity.php'
        assert web.get('/openapi.json').status_code==200


def test_admin_sync_then_read_and_secret_absent(engine, settings):
    c=BrsClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[{'date':'1405-01-01','pc':100,'pf':0}])) )
    with TestClient(create_app(settings,engine,c)) as web:
        headers={'X-Admin-Token':'admin-test'}
        result=web.post('/api/admin/sync',headers=headers,json={'endpoint':'history','params':{'l18':'فملی','type':0}})
        assert result.status_code==200 and result.json()['accepted']==1
        result=web.get('/api/symbols/فملی/history')
        assert result.json()['items'][0]['price_close']=='100.000000'
        assert 'test-key' not in result.text
        assert web.post('/api/admin/sync',headers=headers,json={'endpoint':'transactions','params':{'l18':'فملی'}}).status_code==422
        assert web.post('/api/admin/sync',headers=headers,json={'endpoint':'unknown'}).status_code==422


def test_read_token(engine,settings):
    from pydantic import SecretStr
    settings.read_token=SecretStr('read-test')
    with TestClient(create_app(settings,engine)) as web:
        assert web.get('/api/symbols').status_code==401
        assert web.get('/api/symbols',headers={'X-Api-Token':'read-test'}).status_code==200


def test_scheduler_tehran_and_three_jobs():
    scheduler=build_scheduler(None)
    jobs={j.id:j for j in scheduler.get_jobs()}
    assert set(jobs)=={'intraday','daily','weekly'}
    assert str(scheduler.timezone)=='Asia/Tehran'
    assert '18' in str(jobs['daily'].trigger)
    assert 'fri' in str(jobs['weekly'].trigger)


def test_overlapping_sync_rejected(engine):
    with operation_lock(engine):
        with pytest.raises(BusyError):
            with operation_lock(engine):
                pass


async def test_daily_pipeline_uses_last_trade_date(engine,settings):
    from src.services.sync import SyncService
    from src.scheduler.jobs import Jobs
    settings.selected_symbols='فملی'
    calls=[]
    async def handler(r):
        calls.append(r)
        if r.url.path.endswith('Symbol.php'):
            return httpx.Response(200,json={'l18':'فملی','date':'1405-01-05','date_update':'1405-01-01','pc':100})
        return httpx.Response(200,json=[])
    c=BrsClient(settings,transport=httpx.MockTransport(handler))
    await Jobs(SyncService(engine,c)).run('daily')
    tx=[r for r in calls if r.url.path.endswith('Transaction.php')]
    assert len(tx)==1 and tx[0].url.params['date']=='1405-01-01'
    assert len(calls)==12
    await c.close()


async def test_weekly_pipeline_parameters_and_all_codal_pages(engine,settings):
    from src.services.sync import SyncService
    from src.scheduler.jobs import Jobs
    calls=[]
    async def handler(r):
        calls.append(r)
        if r.url.path.endswith('Announcement.php'):
            return httpx.Response(200,json={'count_page':2,'announcement':[]})
        return httpx.Response(200,json=[])
    c=BrsClient(settings,transport=httpx.MockTransport(handler))
    await Jobs(SyncService(engine,c)).run('weekly')
    nav=[r for r in calls if r.url.path.endswith('Nav.php')]
    codal=[r for r in calls if r.url.path.endswith('Announcement.php')]
    physical=[r for r in calls if r.url.path.endswith('Physical.php')]
    assert len(nav)==2 and all('l18' in r.url.params for r in nav)
    assert [r.url.params['page'] for r in codal]==['1','2']
    assert physical[0].url.params['date_start']<=physical[0].url.params['date_end']
    await c.close()
