"""Finite public endpoint probe. This script never loads .env or accepts API keys."""
import concurrent.futures
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx

SERVICES = {
 'market_watch': ('/api/ClosingPrice/GetMarketWatch', {'market':0,'paperTypes[0]':1,'paperTypes[1]':2,'paperTypes[2]':8,'showTraded':'true','withBestLimits':'true','hEven':0,'RefID':0}, 'marketwatch'),
 'client_all': ('/api/ClientType/GetClientTypeAll', {}, 'clientTypeAllDto'),
 'indices': ('/api/Index/GetIndexB1LastAll/SelectedIndexes/1', {}, 'indexB1'),
 'price_history': ('/api/ClosingPrice/GetClosingPriceDailyList/35425587644337450/0', {}, 'closingPriceDaily'),
}


def probe(item):
    host, name, path, query, expected = item
    record={'host':host,'endpoint':name,'path':path,'checked_at':datetime.now(timezone.utc).isoformat()}
    try:
        r=httpx.get(host+path,params=query,timeout=12,follow_redirects=False,
            headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
                     'Accept':'application/json,text/plain,*/*','Referer':'https://www.tsetmc.com/'})
        record.update(http_status=r.status_code,bytes=len(r.content),content_type=r.headers.get('content-type'),sha256=hashlib.sha256(r.content).hexdigest())
        try:
            data=r.json()
            rows=data.get(expected) if isinstance(data,dict) else None
            record.update(json_valid=True,expected_key=expected,records=len(rows) if isinstance(rows,list) else None,
                          data_received=r.status_code==200 and isinstance(rows,list) and len(rows)>0)
        except ValueError:
            record.update(json_valid=False,data_received=False)
    except httpx.TransportError as e:
        record.update(error_kind=type(e).__name__,data_received=False)
    return record


def main():
    calls=[(host,name,path,query,key) for host in ('https://cdn.tsetmc.com','https://cdn10.tsetmc.com')
        for name,(path,query,key) in SERVICES.items()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(probe,calls))
    report={'environment':'GitHub Actions runner','api_key_used':False,'calls':rows,
            'any_data_received':any(r['data_received'] for r in rows)}
    Path('public-tsetmc-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('TSETMC_PROBE_REPORT='+json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
