import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from src.api.tsetmc import TseClient, CATALOG
from src.api.client import UpstreamError
from src.repositories.models import provider_requests, market_observations, raw_responses, sync_errors, symbols, now
from src.repositories.database import upsert
from src.services.normalization import jalali_date, clock, symbol, digest
from src.services.mapper import map_rows, ensure_symbol


def row_list(payload):
    if isinstance(payload,list):
        return payload
    if isinstance(payload,dict):
        for value in payload.values():
            if isinstance(value,list): return value
        # Common single-object envelopes; a primitive metadata field is ignored.
        for key,value in payload.items():
            if isinstance(value,dict) and not key.startswith('_'):return [value]
        return [payload] if payload else []
    return []


def pick(row,*keys):
    for k in keys:
        if row.get(k) is not None:return row[k]
    return None


class TseSync:
    def __init__(self,engine,client:TseClient):
        self.engine,self.client=engine,client

    async def sync(self,endpoint,path_params=None,query=None):
        self.client.request(endpoint,path_params,query)
        params={'path':path_params or {},'query':query or {}}
        with self.engine.begin() as conn:
            request_id=conn.execute(provider_requests.insert().values(source='tsetmc',endpoint=endpoint,params=params,status='running').returning(provider_requests.c.id)).scalar_one()
        try:
            result=await self.client.get(endpoint,path_params,query)
        except UpstreamError as e:
            with self.engine.begin() as conn:
                conn.execute(provider_requests.update().where(provider_requests.c.id==request_id).values(status='failed',error_kind=e.kind,http_status=e.status))
            raise
        return self.store(result,params,request_id)

    def store(self,result,params,request_id):
        from src.repositories.database import json_default
        from sqlalchemy.exc import DataError,IntegrityError
        import json
        source='tsetmc'
        endpoint=result.endpoint
        data_class='HISTORICAL' if any(x in endpoint.lower() for x in ('history','historical','archive','daily_list','daily_all','calendar','adjust')) else 'LIVE'
        accepted=rejected=0
        with self.engine.begin() as conn:
            raw_id=conn.execute(raw_responses.insert().values(source=source,endpoint='tsetmc',params={'endpoint':endpoint,**params},payload=result.payload).returning(raw_responses.c.id)).scalar_one()
            rows=row_list(result.payload) if result.format=='json' else []
            for row in rows:
                try:
                    with conn.begin_nested():
                        if not isinstance(row,dict):raise ValueError('not_object')
                        instrument=row.get('instrument') or {}
                        code=pick(row,'insCode','id') or params['path'].get('InsCode')
                        code=str(code) if code is not None else None
                        name=pick(row,'lVal18AFC','lVal18','lva') or pick(instrument,'lVal18AFC','lVal18')
                        if not name and code:
                            name=conn.execute(select(symbols.c.symbol_l18).where(symbols.c.ins_code==code).limit(1)).scalar_one_or_none()
                        date=pick(row,'dEven','deven','date','dateUpdate')
                        date=date or params['path'].get('DEven')
                        d=jalali_date(date) if date else None
                        h=pick(row,'hEven','hEvenPDrCotVal')
                        tm=clock(str(h).zfill(6)) if h is not None else ''
                        quality=[] if d else ['source_date_missing']
                        if d:
                            from src.services.normalization import today
                            if data_class=='LIVE' and d!=today():quality.append('stale_source_date')
                        obs={'natural_key':digest(source,endpoint,code,d,tm,row),'request_id':request_id,'source':source,
                            'endpoint':endpoint,'instrument_code':code,'symbol':symbol(name) if name else None,
                            'date_shamsi':d,'time_shamsi':tm,'data_class':data_class,'quality':quality,'raw':row}
                        upsert(conn,market_observations,obs,['natural_key'])
                        if name:
                            ref={'l18':name,'l30':pick(row,'lVal30','lvc') or instrument.get('lVal30')}
                            if code:ref['id']=code
                            ensure_symbol(conn,name,ref)
                        self.normalize(conn,endpoint,row,name,code,d,tm,raw_id)
                        accepted+=1
                except (ValueError,TypeError,DataError,IntegrityError):
                    rejected+=1
                    conn.execute(sync_errors.insert().values(raw_id=raw_id,endpoint='tsetmc',error_kind='invalid_tsetmc_record',raw=row))
            status='partial' if rejected else 'success' if rows else 'empty' if result.payload in (None,[],{}) else 'archived'
            conn.execute(provider_requests.update().where(provider_requests.c.id==request_id).values(
                status=status,http_status=result.status,origin=result.origin,format=result.format,
                source_hash=hashlib.sha256(result.content).hexdigest(),payload=result.payload,accepted=accepted,rejected=rejected))
        return {'request_id':request_id,'raw_id':raw_id,'source':source,'endpoint':endpoint,'status':status,
                'accepted':accepted,'rejected':rejected,'format':result.format,'data_class':data_class}

    @staticmethod
    def normalize(conn,endpoint,row,name,code,d,tm,raw_id):
        # Unmapped families remain fully available as provider payload + observations.
        if endpoint=='indices':
            if not row.get('lVal30') or row.get('xDrNivJIdx004') is None:return
            r={'name':row['lVal30'],'index':row['xDrNivJIdx004'],'index_change':row.get('indexChange'),
               'index_change_percent':row.get('xVarIdxJRfV'),'time':tm}
            if d:r['date']=d
            map_rows(conn,'indices',r,{'type':1},raw_id,source='tsetmc');return
        if not name:return
        if endpoint in ('price_history','closing_info','market_watch'):
            mapping={'pf':('priceFirst','pf'),'pmax':('priceMax',),'pmin':('priceMin',),
                'pc':('pClosing','pcl'),'pl':('pDrCotVal','pdv'),'py':('priceYesterday','py'),
                'tno':('zTotTran','ztt'),'tvol':('qTotTran5J','qtc'),'tval':('qTotCap','qtj')}
            r={k:pick(row,*keys) for k,keys in mapping.items()}
            r.update(l18=name,time=tm)
            if d:r['date']=d
            if endpoint=='price_history' and d:
                map_rows(conn,'history',r,{'l18':name,'type':0},raw_id,source='tsetmc')
            elif endpoint!='price_history':
                map_rows(conn,'symbol',r,{'l18':name},raw_id,source='tsetmc')
        elif endpoint in ('client_history','client_all') and d:
            r={'date':d}
            for side in ('Buy','Sell'):
                for group in ('I','N'):
                    for suffix in (f'Count{group}',f'{group}_Volume',f'{group}_Value'):
                        dest=f'{side}_{suffix}'
                        r[dest]=pick(row,dest,side.lower()+'_'+suffix,side.lower()+'_'+suffix[0].lower()+suffix[1:])
            map_rows(conn,'history',r,{'l18':name,'type':1},raw_id,source='tsetmc')
        elif endpoint=='trade_history' and d:
            r={'date':d,'time':tm,'row':pick(row,'nTran','row'),'price':pick(row,'pTran','price'),
                'volume':pick(row,'qTitTran','volume'),'canceled':pick(row,'canceled','isCanceled') or 0}
            # c even=0 is not silently interpreted without a verified contract.
            map_rows(conn,'transactions',r,{'l18':name,'date':d},raw_id,source='tsetmc')
