import pytest
from sqlalchemy import select, func
from src.repositories.models import TABLES, symbols, raw_responses, sync_runs, sync_errors
from src.services.normalization import jalali_date, number
from conftest import service_for

CASES = [
 ('symbols', {'type':1}, [{'l18':'فملی','id': '99999999999999999','l30':'شرکت'}], 'symbols', 1),
 ('indices', {'type':1}, {'date':'1405-01-01','time':'12:00','index':123.5}, 'index_values', 1),
 ('symbol', {'l18':'فملی'}, {'l18':'فملی','date':'1405-01-01','pl':0,'pc':12}, 'symbol_snapshots', 1),
 ('nav', {'l18':'اهرم'}, {'date':'1405-01-01','psubtran':121,'predtran':120}, 'etf_nav', 1),
 ('options', {}, [{'l18':'ضفملی','date_end':'1405-12-01','price_strike':1000,'interest_open':12,'pl':10}], 'tse_options', 1),
 ('history', {'type':0,'l18':'فملی'}, [{'date':'1405-01-01','pc':100,'pf':0,'tvol':10}], 'price_history', 1),
 ('history', {'type':1,'l18':'فملی'}, [{'date':'1405-01-01','Buy_CountI':1,'Buy_I_Volume':10,'Buy_I_Value':100}], 'client_type_history', 1),
 ('candles', {'type':3,'l18':'فملی'}, {'count':1,'candles':[{'date':'1405/01/01','open':10,'high':12,'low':9,'close':11,'volume':4}]}, 'candlesticks', 1),
 ('transactions', {'l18':'فملی','date':'1405-01-01'}, [{'row':1,'time':'09:01','price':10,'volume':5,'canceled':0}], 'transactions', 1),
 ('shareholders', {'l18':'فملی','date':'1405-01-01'}, [{'name':'دارنده','percent':1,'volume':100}], 'shareholders', 1),
 ('codal', {'page':1}, {'count_page':1,'announcement':[{'l18':'فملی','date_publish':'۱۴۰۵/۰۱/۰۱','title':'گزارش','link':'https://codal.ir/report/1'}]}, 'codal_announcements', 1),
 ('ime_futures', {}, {'successful':True,'data':[{'contract_code':'FUT1','date_update':'1405-01-01','pl':10,'interest_open':2}]}, 'ime_futures', 1),
 ('ime_options', {}, {'successful':True,'data':[{'date_update':'1405-01-01','price_strike':100,'call_contract_code':'C1','put_contract_code':'P1','call_pl':3,'put_pl':None}]}, 'ime_options', 2),
 ('ime_certificates', {}, {'data':[{'contract_code':'CERT1','date_update':'1405-01-01','pl':4,'tval':100,'tval_unit':'هزار ریال'}]}, 'ime_certificates', 1),
 ('ime_funds', {}, [{'l18':'عیار','pl':100,'tvol':10}], 'ime_funds', 1),
 ('ime_physical', {'date_start':'1405-01-01','date_end':'1405-01-01'}, [{'l18':'STEEL','code_offer':12,'date_trade':'1405/01/01','volume_contract':10.5,'tval':100}], 'ime_physical', 1),
 ('commodities', {}, [{'symbol':'XAUUSD','date':'1405/01/01','price':'2500.125','unit':'دلار'}], 'commodities', 1),
]


@pytest.mark.parametrize('endpoint,params,payload,table_name,count', CASES)
async def test_all_adapters_store_and_upsert(engine, settings, endpoint, params, payload, table_name, count):
    service = service_for(engine, settings, payload)
    first = await service.sync(endpoint, **params)
    second = await service.sync(endpoint, **params)
    assert first['accepted'] == second['accepted'] == count
    assert first['rejected'] == second['rejected'] == 0
    table = symbols if table_name == 'symbols' else TABLES[table_name]
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(table)).scalar_one() == count
        assert conn.execute(select(func.count()).select_from(raw_responses)).scalar_one() == 2
    await service.client.close()


async def test_daily_price_updates_not_duplicates_and_zero_survives(engine, settings):
    service = service_for(engine, settings, [{'date':'1405-01-01','pc':100,'pf':0,'time':'12:00'}])
    await service.sync('history', type=0, l18='فملی')
    service.client = service_for(engine, settings, [{'date':'1405-01-01','pc':102,'pf':0,'time':'13:00'}]).client
    await service.sync('history', type=0, l18='فملی')
    with engine.connect() as conn:
        rows = conn.execute(select(TABLES['price_history'])).mappings().all()
        assert len(rows) == 1 and rows[0]['price_close'] == 102 and rows[0]['price_first'] == 0
    await service.client.close()


async def test_invalid_row_is_quarantined_other_rows_commit(engine, settings):
    service = service_for(engine, settings, [{'date':'1405-01-01','pc':100}, {'date':'1405-13-01','pc':100}, {'date':'1405-01-02','pc':'NaN'}])
    result = await service.sync('history', l18='فملی', type=0)
    assert result['accepted'] == 1 and result['rejected'] == 2 and result['status'] == 'partial'
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(sync_errors)).scalar_one() == 2
    await service.client.close()


async def test_canceled_trade_updates_same_identity(engine, settings):
    s = service_for(engine, settings, [{'row':1,'time':'09:00','price':10,'volume':1,'canceled':0}])
    await s.sync('transactions', l18='فملی', date='1405-01-01')
    await s.client.close()
    s = service_for(engine, settings, [{'row':1,'time':'09:00','price':10,'volume':1,'canceled':1}])
    await s.sync('transactions', l18='فملی', date='1405-01-01')
    with engine.connect() as conn:
        rows = conn.execute(select(TABLES['transactions'])).mappings().all()
        assert len(rows) == 1 and rows[0]['canceled'] is True
    await s.client.close()


async def test_unknown_envelope_archived_and_run_failed(engine, settings):
    from src.api.client import UpstreamError
    s = service_for(engine, settings, {'unexpected':'schema'})
    with pytest.raises(UpstreamError):
        await s.sync('symbols')
    with engine.connect() as conn:
        assert conn.execute(select(raw_responses.c.id)).scalar_one()
        assert conn.execute(select(sync_runs.c.status)).scalar_one() == 'failed'
    await s.client.close()


async def test_codal_pagination_fetches_all_pages(engine, settings):
    import httpx
    from src.api.client import BrsClient
    from src.services.sync import SyncService
    pages=[]
    async def handler(r):
        p=int(r.url.params['page']);pages.append(p)
        return httpx.Response(200,json={'count_page':3,'announcement':[{'l18':'فملی','date_publish':'1405-01-01','title':'گزارش','link':f'https://codal.ir/{p}'}]})
    client=BrsClient(settings, transport=httpx.MockTransport(handler))
    result=await SyncService(engine,client).codal_pages()
    assert pages==[1,2,3] and result['status']=='complete'
    await client.close()


@pytest.mark.parametrize('raw,expected', [('۱۴۰۵/۰۱/۰۱','1405-01-01'),('20260321','1405-01-01'),('14050101','1405-01-01')])
def test_date_calendar_normalization(raw,expected):
    assert jalali_date(raw)==expected


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '1.1', '-1', '9999999999999999999999'])
def test_invalid_integer_not_silently_coerced(value):
    with pytest.raises(ValueError):
        number(value,integer=True,nonnegative=True)


async def test_official_intraday_envelope_uses_provider_context_not_today(engine, settings):
    import httpx
    from src.api.client import BrsClient
    from src.services.sync import SyncService
    calls=[]
    async def handler(r):
        calls.append(r.url.path)
        if r.url.path.endswith('Symbol.php'):
            return httpx.Response(200,json={'l18':'فملی','date':'1405-01-05','date_update':'1405-01-01','pc':100})
        return httpx.Response(200,json={'l18':'فملی','type':1,'count':1,'candle_intraday':[{'time':'12:28','open':100,'high':110,'low':90,'close':105,'volume':20}]})
    c=BrsClient(settings,transport=httpx.MockTransport(handler))
    result=await SyncService(engine,c).sync('candles',l18='فملی',type=1)
    assert result['accepted']==1
    with engine.connect() as conn:
        r=conn.execute(select(TABLES['candlesticks'])).mappings().one()
        assert r['date_shamsi']=='1405-01-01' and r['date_basis']=='provider_context'
    assert len(calls)==2
    await c.close()


async def test_adjusted_and_unadjusted_candles_kept_separate(engine,settings):
    payload={'l18':'فملی','type':2,'candle_daily':[{'date':'1405-01-01','open':10,'high':12,'low':9,'close':11}]}
    s=service_for(engine,settings,payload)
    await s.sync('candles',l18='فملی',type=2)
    await s.sync('candles',l18='فملی',type=3)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(TABLES['candlesticks'])).scalar_one()==2
    await s.client.close()
