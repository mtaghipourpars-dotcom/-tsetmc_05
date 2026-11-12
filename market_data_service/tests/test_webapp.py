import httpx
import pytest
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from src.web.app import create_app
from src.api.tsetmc import TseClient
from src.api.client import BrsClient
from src.services.tsetmc_sync import TseSync
from src.services.sync import SyncService
from src.services.collection import Collections,symbol_plan,add_task
from src.repositories.models import collection_jobs,collection_tasks,symbols,TABLES
from src.services.import_repository import import_history
from src.services.mapper import ensure_symbol


def make_queue(engine,settings,handler):
    tse=TseClient(settings,transport=httpx.MockTransport(handler))
    brs=BrsClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[])))
    return Collections(engine,TseSync(engine,tse),SyncService(engine,brs)),tse,brs


def test_webapp_assets_and_durable_job_api(engine,settings):
    with TestClient(create_app(settings,engine)) as web:
        root=web.get('/')
        assert root.status_code==200 and 'دیدبان' in root.text and 'dir="rtl"' in root.text
        assert web.get('/static/app.js').status_code==200
        assert web.get('/static/app.css').status_code==200
        assert web.get('/api/dashboard').json()['records']==0
        assert web.post('/api/admin/collections',json={'source':'tsetmc','scope':'all'}).status_code==401
        result=web.post('/api/admin/collections',headers={'X-Admin-Token':'admin-test'},json={'source':'tsetmc','scope':'all'})
        assert result.status_code==202
        job_id=result.json()['job_id']
        assert web.get('/api/collections').json()['items'][0]['total']>3
        assert web.get('/api/dashboard').json()['active_jobs']==1
        pause=web.post(f'/api/admin/collections/{job_id}/pause',headers={'X-Admin-Token':'admin-test'})
        assert pause.json()['status']=='paused'
        resume=web.post(f'/api/admin/collections/{job_id}/resume',headers={'X-Admin-Token':'admin-test'})
        assert resume.json()['status']=='queued'
        assert web.post('/api/admin/collections',headers={'X-Admin-Token':'admin-test'},json={'scope':'selected','symbols':[]}).status_code==422
        assert web.post('/api/admin/collections',headers={'X-Admin-Token':'admin-test'},json={'date_start':'1405-01-01'}).status_code==422


async def test_complete_collection_discovers_symbols_stores_history_and_finishes(engine,settings):
    calls=[]
    async def handler(r):
        calls.append(r.url.path)
        if 'GetMarketWatch' in r.url.path:
            return httpx.Response(200,json={'marketwatch':[{'insCode':'35425587644337450','lva':'فملی','lvc':'ملی مس','pcl':100,'dEven':20261111}]})
        if 'GetClosingPriceDailyList/' in r.url.path:
            return httpx.Response(200,json={'closingPriceDaily':[{'dEven':20261111,'pClosing':100,'priceFirst':90,'qTotTran5J':10}]})
        return httpx.Response(200,json=[])
    queue,tse,brs=make_queue(engine,settings,handler)
    job=queue.create()
    for _ in range(200):
        if not await queue.process_one():break
    result=queue.detail(job)
    assert result['status']=='completed' and result['percent']==100
    assert any('GetTradeHistory/35425587644337450/20261111' in path for path in calls)
    assert any('GetInstrumentShareHolderLast' in path for path in calls)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(TABLES['price_history'])).scalar_one()==1
        assert conn.execute(select(symbols.c.symbol_l18)).scalar_one()=='فملی'
    # Another manager sees persisted state, not an in-memory task queue.
    assert Collections(engine,queue.tse,queue.brs).detail(job)['status']=='completed'
    await tse.close();await brs.close()


async def test_network_failure_pauses_job_and_resume_keeps_completed_work(engine,settings):
    settings.max_retries=0
    queue,tse,brs=make_queue(engine,settings,lambda r:httpx.Response(503))
    job=queue.create()
    assert await queue.process_one()
    result=queue.detail(job)
    assert result['status']=='paused' and result['counts']['failed']==1
    assert not await queue.process_one()
    queue.change(job,'resume')
    assert queue.detail(job)['counts'].get('failed',0)==0
    assert queue.detail(job)['status']=='queued'
    await tse.close();await brs.close()


def test_plan_deduplicates_aliases_and_does_not_use_stock_id_as_index():
    from src.api.tsetmc import CATALOG
    plan,deferred=symbol_plan('فملی','35425587644337450','20261111')
    assert any(name=='price_history' for name,_ in plan)
    assert not any(CATALOG[name]['group']=='Index' or 'GetIndexCompany' in CATALOG[name]['path'] for name,_ in plan)
    assert not any('GetClosingPriceDailyListCSV' in CATALOG[name]['path'] for name,_ in plan)
    keys=[(CATALOG[name]['path'].format_map({k:str(v) for k,v in params.items()}).lower().rstrip('/')) for name,params in plan]
    assert len(keys)==len(set(keys))
    assert all('DEven' not in p and 'dEven' not in p for _,p in symbol_plan('فملی','35425587644337450')[0])


def test_task_deduplication_never_resets_success(engine):
    queue=Collections(engine,None,None);job=queue.create(scope='selected',names=['فملی'])
    with engine.begin() as conn:
        add_task(conn,job,'tsetmc','price_history',{'path':{'InsCode':'123'},'query':{}},'فملی')
        conn.execute(collection_tasks.update().where(collection_tasks.c.endpoint=='price_history').values(status='success'))
        add_task(conn,job,'tsetmc','price_history',{'path':{'InsCode':'123'},'query':{}},'فملی')
    with engine.connect() as conn:
        assert conn.execute(select(collection_tasks.c.status).where(collection_tasks.c.endpoint=='price_history')).scalar_one()=='success'


def test_stock_queries_and_csv_use_stored_data(engine,settings):
    from src.repositories.models import raw_responses
    from src.services.mapper import map_rows
    with engine.begin() as conn:
        raw=conn.execute(raw_responses.insert().values(source='repository',endpoint='test',params={},payload=[]).returning(raw_responses.c.id)).scalar_one()
        map_rows(conn,'history',{'date':'1405-08-20','pc':100,'py':90,'tvol':100}, {'l18':'فملی','type':0},raw,source='repository')
    with TestClient(create_app(settings,engine)) as web:
        stocks=web.get('/api/stocks?q=فملي').json()
        assert stocks['total']==1 and stocks['items'][0]['price_close']=='100.000000'
        assert web.get('/api/stocks/فملی').json()['coverage']['price_history']==1
        assert web.get('/api/stocks/ناشناخته').status_code==404
        csv=web.get('/api/stocks/فملی/export')
        assert csv.status_code==200 and 'text/csv' in csv.headers['content-type'] and 'repository' in csv.text
        assert web.get('/api/datasets').json()['items']
