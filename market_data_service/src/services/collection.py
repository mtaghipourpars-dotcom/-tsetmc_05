"""A durable, single-consumer acquisition queue with explicit coverage reporting."""
from datetime import timedelta
import re
import jdatetime
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sq_insert
from src.repositories.models import collection_jobs as jobs, collection_tasks as tasks, symbols, TABLES, now
from src.services.normalization import digest, symbol, jalali_date
from src.api.tsetmc import CATALOG
from src.api.client import UpstreamError
from src.services.locking import operation_lock, BusyError

CORE_FIRST=['instrument_info','closing_info','price_history','price_adjustments']


def add_task(conn,job_id,kind,endpoint,params,name=None):
    values={'job_id':job_id,'task_key':digest(kind,endpoint,params,name),'kind':kind,'endpoint':endpoint,
            'symbol':name,'params':params,'status':'queued'}
    insert=pg_insert if conn.dialect.name=='postgresql' else sq_insert
    conn.execute(insert(tasks).values(**values).on_conflict_do_nothing(index_elements=['job_id','task_key']))


def canonical_path(entry):
    return re.sub(r'\{[^}]+\}', '{}', entry['path']).lower().rstrip('/')


def symbol_plan(name,code,last_day=None):
    plans=[];deferred=[];seen=set()
    entries=sorted(CATALOG.values(),key=lambda r:(CORE_FIRST.index(r['id']) if r['id'] in CORE_FIRST else 20,r['id']))
    for entry in entries:
        if entry['origin']!='cdn.tsetmc.com' or entry['group']=='Index' or 'GetIndexCompany' in entry['path']:continue
        if 'GetClosingPriceDailyList' in entry['path'] and entry['id']!='price_history':continue
        fields=entry['parameters'];lower={p.lower() for p in fields}
        if not lower.intersection({'inscode','symbol'}):continue
        values={};unknown=[]
        for field in fields:
            key=field.lower()
            if key=='inscode':values[field]=code
            elif key=='symbol':values[field]=name
            elif key=='deven' and last_day:values[field]=last_day
            elif key=='top':values[field]=1000
            elif key=='resolution':values[field]='D'
            elif key=='prependcol':values[field]=0
            else:unknown.append(field)
        if unknown:
            deferred.append({'endpoint':entry['id'],'missing_parameters':unknown});continue
        identity=(entry['path'].format_map({k:str(v) for k,v in values.items()}).lower().rstrip('/'),entry['query_template'].format_map({k:str(v) for k,v in values.items()}))
        if identity in seen:continue
        seen.add(identity)
        plans.append((entry['id'],values))
    return plans,deferred


class Collections:
    def __init__(self,engine,tse,brs):
        self.engine,self.tse,self.brs=engine,tse,brs

    def create(self,source='tsetmc',scope='all',names=None,options=None):
        names=list(dict.fromkeys(symbol(n) for n in (names or []) if str(n).strip()))
        options=options or {}
        if source not in ('tsetmc','brsapi') or scope not in ('all','selected'):raise ValueError('Invalid collection scope/source')
        if scope=='selected' and not names:raise ValueError('Select at least one symbol')
        if bool(options.get('date_start')) != bool(options.get('date_end')):raise ValueError('Both dates are required')
        if options.get('date_start'):
            start=jalali_date(options['date_start']);end=jalali_date(options['date_end'])
            if start>end:raise ValueError('Invalid date range')
            options={**options,'date_start':start,'date_end':end}
        with self.engine.begin() as conn:
            job=conn.execute(jobs.insert().values(source=source,scope=scope,symbols=names,options=options,status='queued').returning(jobs.c.id)).scalar_one()
            if source=='tsetmc':
                seen=set()
                for endpoint in ('market_watch','client_all','indices'):
                    add_task(conn,job,'tsetmc',endpoint,{'path':{},'query':{}})
                    seen.add(canonical_path(CATALOG[endpoint]))
                for entry in CATALOG.values():
                    key=canonical_path(entry)
                    if entry['origin']=='cdn.tsetmc.com' and not entry['parameters'] and key not in seen and entry['group'] not in ('Learning','Supervision'):
                        add_task(conn,job,'tsetmc',entry['id'],{'path':{},'query':{}})
                        seen.add(key)
            else:
                for kind in (1,2,3,4,5):add_task(conn,job,'brsapi','symbols',{'type':kind})
                for kind in (1,2,3):add_task(conn,job,'brsapi','indices',{'type':kind})
                for endpoint in ('options','ime_futures','ime_options','ime_certificates','ime_funds','ime_physical','commodities'):
                    add_task(conn,job,'brsapi',endpoint,{})
                add_task(conn,job,'brsapi','codal',{'_all_pages':True})
            add_task(conn,job,'expand','universe',{})
        return job

    def change(self,job_id,action):
        with self.engine.begin() as conn:
            job=conn.execute(select(jobs).where(jobs.c.id==job_id)).mappings().first()
            if not job:raise LookupError('Collection not found')
            if action=='pause':
                conn.execute(jobs.update().where(jobs.c.id==job_id).values(status='paused',updated_at=now()))
            elif action=='resume':
                actionable=conn.execute(select(func.count()).select_from(tasks).where(tasks.c.job_id==job_id,tasks.c.status.in_(['queued','failed','running']))).scalar_one()
                if not actionable:raise ValueError('Start a new collection for another acquisition')
                if job['status']=='running':raise ValueError('Collection is already running')
                conn.execute(tasks.update().where(tasks.c.job_id==job_id,tasks.c.status.in_(['failed','running'])).values(status='queued',error_kind=None,updated_at=now()))
                conn.execute(jobs.update().where(jobs.c.id==job_id).values(status='queued',last_error=None,updated_at=now()))
            else:raise ValueError('Invalid action')

    def detail(self,job_id):
        with self.engine.connect() as conn:
            job=conn.execute(select(jobs).where(jobs.c.id==job_id)).mappings().first()
            if not job:raise LookupError('Collection not found')
            counts=dict(conn.execute(select(tasks.c.status,func.count()).where(tasks.c.job_id==job_id).group_by(tasks.c.status)).all())
            rows=conn.execute(select(tasks).where(tasks.c.job_id==job_id).order_by(tasks.c.id.desc()).limit(100)).mappings().all()
        total=sum(counts.values());done=sum(counts.get(k,0) for k in ('success','empty','archived','partial','failed','skipped'))
        return {**dict(job),'counts':counts,'total':total,'done':done,'percent':round(done/total*100) if total else 0,'tasks':[dict(r) for r in rows]}

    def claim(self):
        with self.engine.begin() as conn:
            # A crashed worker's lease becomes claimable after ten minutes.
            conn.execute(tasks.update().where(tasks.c.status=='running',tasks.c.updated_at<now()-timedelta(minutes=10)).values(status='queued'))
            query=select(tasks).join(jobs,tasks.c.job_id==jobs.c.id).where(tasks.c.status=='queued',jobs.c.status.in_(['queued','running'])).order_by(tasks.c.id).limit(1)
            if conn.dialect.name=='postgresql':query=query.with_for_update(of=tasks,skip_locked=True)
            task=conn.execute(query).mappings().first()
            if not task:return None
            conn.execute(tasks.update().where(tasks.c.id==task['id']).values(status='running',attempts=tasks.c.attempts+1,updated_at=now()))
            conn.execute(jobs.update().where(jobs.c.id==task['job_id']).values(status='running',updated_at=now()))
            return dict(task)

    def expand(self,task):
        with self.engine.begin() as conn:
            job=conn.execute(select(jobs).where(jobs.c.id==task['job_id'])).mappings().one()
            if task['endpoint']=='universe':
                names=job['symbols'] if job['scope']=='selected' else list(conn.execute(select(symbols.c.symbol_l18).where(symbols.c.is_active.is_(True)).order_by(symbols.c.id)).scalars())
                for name in names:add_task(conn,job['id'],'expand','symbol',{},name)
                return {'symbols_planned':len(names),'warning':None if names else 'universe_not_available'}
        name=task['symbol']
        if job['source']=='brsapi':
            with self.engine.begin() as conn:
                calls=[('symbol',{'l18':name}),('history',{'l18':name,'type':0}),('history',{'l18':name,'type':1}),
                    *[('candles',{'l18':name,'type':t}) for t in (1,2,3)],('shareholders',{'l18':name})]
                reference=conn.execute(select(symbols.c.symbol_name).where(symbols.c.symbol_l18==name)).scalar_one_or_none()
                if reference and 'صندوق' in reference:calls.append(('nav',{'l18':name}))
                for endpoint,params in calls:add_task(conn,job['id'],'brsapi',endpoint,params,name)
                add_task(conn,job['id'],'expand','brs_dated',{},name)
            return {'requests_planned':len(calls),'deferred':['dated_transactions_require_a_verified_trade_date','NAV_is_only_requested_for_classified_funds']}
        with self.engine.connect() as conn:
            code=conn.execute(select(symbols.c.ins_code).where(symbols.c.symbol_l18==name)).scalar_one_or_none()
        if not code:return {'resolve_name':name}
        # Temporal requests need a provider date; never invent a market date.
        with self.engine.connect() as conn:
            last=conn.execute(select(func.max(TABLES['price_history'].c.date_shamsi)).join(symbols,TABLES['price_history'].c.symbol_id==symbols.c.id).where(symbols.c.symbol_l18==name)).scalar_one_or_none()
        last_day=jdatetime.date.fromisoformat(last).togregorian().strftime('%Y%m%d') if last else None
        plans,deferred=symbol_plan(name,code,last_day)
        with self.engine.begin() as conn:
            for endpoint,params in plans:add_task(conn,job['id'],'tsetmc',endpoint,{'path':params,'query':{}},name)
            add_task(conn,job['id'],'expand','dated',{'code':code},name)
        return {'requests_planned':len(plans),'deferred':deferred}

    async def process_one(self):
        # All network acquisition shares the same cross-process advisory lock.
        try:
            with operation_lock(self.engine):
                task=self.claim()
                if not task:return False
                result={};status='success';error=None
                try:
                    if task['kind']=='expand':
                        if task['endpoint']=='brs_dated':
                            with self.engine.begin() as conn:
                                reference=conn.execute(select(symbols).where(symbols.c.symbol_l18==task['symbol'])).mappings().one()
                                day=reference['raw'].get('date_update')
                                if not day:
                                    day=conn.execute(select(func.max(TABLES['price_history'].c.date_shamsi)).where(TABLES['price_history'].c.symbol_id==reference['id'])).scalar_one_or_none()
                                if day:add_task(conn,task['job_id'],'brsapi','transactions',{'l18':task['symbol'],'date':jalali_date(day)},task['symbol'])
                                result={'trade_date':jalali_date(day) if day else None,'warning':None if day else 'provider_trade_date_not_available'}
                        elif task['endpoint']=='dated':result=self.expand_dated(task)
                        else:
                            result=self.expand(task)
                            if result.get('resolve_name'):
                                await self.tse.sync('instrument_search',{'Query':result['resolve_name']})
                                with self.engine.connect() as conn:
                                    code=conn.execute(select(symbols.c.ins_code).where(symbols.c.symbol_l18==task['symbol'])).scalar_one_or_none()
                                if not code:raise UpstreamError('instrument_not_found')
                                result=self.expand(task)
                        if result.get('warning'):status='partial'
                    elif task['kind']=='tsetmc':
                        result=await self.tse.sync(task['endpoint'],task['params']['path'],task['params']['query'])
                        status=result['status']
                    else:
                        params=dict(task['params'])
                        all_pages=params.pop('_all_pages',False)
                        result=await self.brs.codal_pages(**params) if all_pages else await self.brs.sync(task['endpoint'],**params)
                        status=result.get('status','success')
                        if status=='complete':status='success'
                        if status=='truncated' and result.get('next_page'):
                            with self.engine.begin() as conn:
                                add_task(conn,task['job_id'],'brsapi','codal',{**task['params'],'page':result['next_page']},task['symbol'])
                            result['pagination_continues']=True;status='success'
                except UpstreamError as e:
                    status='failed';error=e.kind
                    if e.status in (401,403,429) or any(x in e.kind for x in ('circuit_open','network','server','account_blocked','missing_key')):
                        with self.engine.begin() as conn:
                            conn.execute(jobs.update().where(jobs.c.id==task['job_id']).values(status='paused',last_error=e.kind,updated_at=now()))
                except Exception:
                    status='failed';error='internal_error'
                with self.engine.begin() as conn:
                    conn.execute(tasks.update().where(tasks.c.id==task['id']).values(status=status,result=result,error_kind=error,updated_at=now()))
                    outstanding=conn.execute(select(func.count()).select_from(tasks).where(tasks.c.job_id==task['job_id'],tasks.c.status.in_(['queued','running']))).scalar_one()
                    if not outstanding:
                        bad=conn.execute(select(func.count()).select_from(tasks).where(tasks.c.job_id==task['job_id'],tasks.c.status.in_(['failed','partial']))).scalar_one()
                        conn.execute(jobs.update().where(jobs.c.id==task['job_id'],jobs.c.status!='paused').values(status='partial' if bad else 'completed',updated_at=now()))
                return True
        except BusyError:return False

    def expand_dated(self,task):
        with self.engine.connect() as conn:
            job=conn.execute(select(jobs).where(jobs.c.id==task['job_id'])).mappings().one()
            last=conn.execute(select(func.max(TABLES['price_history'].c.date_shamsi)).join(symbols,TABLES['price_history'].c.symbol_id==symbols.c.id).where(symbols.c.symbol_l18==task['symbol'])).scalar_one_or_none()
        options=job['options'];dates=[]
        if options.get('date_start'):
            day=jdatetime.date.fromisoformat(options['date_start']);end=jdatetime.date.fromisoformat(options['date_end'])
            while day<=end:
                dates.append(day.togregorian().strftime('%Y%m%d'));day+=timedelta(days=1)
        elif last:dates=[jdatetime.date.fromisoformat(last).togregorian().strftime('%Y%m%d')]
        with self.engine.begin() as conn:
            for day in dates:
                plans,_=symbol_plan(task['symbol'],task['params']['code'],day)
                for endpoint,params in plans:
                    if any(k.lower()=='deven' for k in params):add_task(conn,job['id'],'tsetmc',endpoint,{'path':params,'query':{}},task['symbol'])
        return {'dates_planned':len(dates),'warning':None if dates else 'provider_trade_date_not_available'}
