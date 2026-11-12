from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select,func,or_,case
from src.repositories.models import symbols,TABLES,raw_responses,market_observations,provider_requests,sync_errors,collection_jobs,collection_tasks
from src.repositories.database import page
from src.services.normalization import symbol


class CollectionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source:Literal['tsetmc','brsapi']='tsetmc'
    scope:Literal['all','selected']='all'
    symbols:list[str]=Field(default_factory=list,max_length=10000)
    date_start:str|None=None
    date_end:str|None=None


def router_for(engine,queue,read_auth,admin_auth,settings):
    router=APIRouter()
    def response(value):return jsonable_encoder(value,custom_encoder={Decimal:str})
    history=TABLES['price_history']
    latest=history.alias('latest_price')
    latest_id=select(history.c.id).where(history.c.symbol_id==symbols.c.id).order_by(
        history.c.date_shamsi.desc(),case((history.c.source=='tsetmc',0),(history.c.source=='brsapi',1),else_=2),history.c.id.desc()
    ).limit(1).correlate(symbols).scalar_subquery()
    joined=symbols.outerjoin(latest,latest.c.id==latest_id)

    @router.get('/api/dashboard',dependencies=[Depends(read_auth)])
    def dashboard():
        with engine.connect() as conn:
            datasets={k:conn.execute(select(func.count()).select_from(t)).scalar_one() for k,t in TABLES.items()}
            archive_count=conn.execute(select(func.count()).select_from(raw_responses)).scalar_one()
            observation_count=conn.execute(select(func.count()).select_from(market_observations)).scalar_one()
            count=conn.execute(select(func.count()).select_from(symbols)).scalar_one()
            requests=conn.execute(select(provider_requests).order_by(provider_requests.c.id.desc()).limit(8)).mappings().all()
            requests=[{k:v for k,v in r.items() if k!='payload'} for r in requests]
            dates=conn.execute(select(func.min(history.c.date_shamsi),func.max(history.c.date_shamsi))).one()
            source_counts=conn.execute(select(history.c.source,func.count()).group_by(history.c.source)).all()
            active=conn.execute(select(func.count()).select_from(collection_jobs).where(collection_jobs.c.status.in_(['running','queued']))).scalar_one()
        return response({'symbols':count,'records':sum(datasets.values())+observation_count,'price_records':datasets['price_history'],
            'archives':archive_count,'observations':observation_count,'datasets':datasets,'date_start':dates[0],'date_end':dates[1],
            'sources':dict(source_counts),'active_jobs':active,'recent_requests':requests,
            'database':'connected','provider':settings.data_provider,'brs_key_configured':bool(settings.brs_api_key.get_secret_value()),
            'checked_at':datetime.now(timezone.utc)})

    @router.get('/api/stocks',dependencies=[Depends(read_auth)])
    def stocks(q:str='',limit:int=Query(30,ge=1,le=200),offset:int=Query(0,ge=0)):
        conditions=[]
        if q:
            value=symbol(q)
            conditions=[or_(symbols.c.symbol_l18.contains(value,autoescape=True),symbols.c.symbol_name.contains(value,autoescape=True),symbols.c.ins_code==value)]
        query=select(symbols,latest.c.price_close,latest.c.price_last,latest.c.price_yesterday,latest.c.volume,
            latest.c.value,latest.c.date_shamsi,latest.c.source).select_from(joined).where(*conditions).order_by(symbols.c.symbol_l18)
        with engine.connect() as conn:
            count=conn.execute(select(func.count()).select_from(symbols).where(*conditions)).scalar_one()
            rows=conn.execute(query.limit(limit).offset(offset)).mappings().all()
        return response({'total':count,'items':[dict(r) for r in rows],'limit':limit,'offset':offset})

    @router.get('/api/stocks/{l18}',dependencies=[Depends(read_auth)])
    def stock_detail(l18:str):
        with engine.connect() as conn:
            stock=conn.execute(select(symbols).where(symbols.c.symbol_l18==symbol(l18))).mappings().first()
            if not stock:raise HTTPException(404,'Symbol not found')
            rn=func.row_number().over(partition_by=history.c.date_shamsi,
                order_by=[case((history.c.source=='tsetmc',0),(history.c.source=='brsapi',1),else_=2),history.c.id.desc()]).label('n')
            all_history=select(history,rn).where(history.c.symbol_id==stock['id']).subquery()
            prices=conn.execute(select(all_history).where(all_history.c.n==1).order_by(all_history.c.date_shamsi.desc()).limit(180)).mappings().all()
            coverage={k:conn.execute(select(func.count()).select_from(t).where(t.c.symbol_id==stock['id'])).scalar_one() for k,t in TABLES.items()}
            conditions=[market_observations.c.symbol==stock['symbol_l18']]
            if stock['ins_code']:conditions.append(market_observations.c.instrument_code==stock['ins_code'])
            observations=conn.execute(select(market_observations).where(or_(*conditions)).order_by(market_observations.c.id.desc()).limit(60)).mappings().all()
        return response({'symbol':dict(stock),'history':[dict(r) for r in prices], 'coverage':coverage,'observations':[dict(r) for r in observations]})

    @router.get('/api/collections',dependencies=[Depends(read_auth)])
    def collections():
        with engine.connect() as conn:
            ids=list(conn.execute(select(collection_jobs.c.id).order_by(collection_jobs.c.id.desc()).limit(20)).scalars())
        return response({'items':[queue.detail(i) for i in ids]})

    @router.post('/api/admin/collections',dependencies=[Depends(admin_auth)],status_code=202)
    def start_collection(body:CollectionRequest):
        try:
            job=queue.create(body.source,body.scope,body.symbols,{'date_start':body.date_start,'date_end':body.date_end})
        except ValueError as e:raise HTTPException(422,str(e)) from None
        return {'job_id':job,'status':'queued'}

    @router.post('/api/admin/collections/{job_id}/{action}',dependencies=[Depends(admin_auth)])
    def collection_action(job_id:int,action:Literal['pause','resume']):
        try:queue.change(job_id,action)
        except LookupError:raise HTTPException(404,'Collection not found') from None
        except ValueError as e:raise HTTPException(409,str(e)) from None
        return response(queue.detail(job_id))

    @router.get('/api/stocks/{l18}/export',dependencies=[Depends(read_auth)])
    def export(l18:str):
        import csv,io
        with engine.connect() as conn:
            sid=conn.execute(select(symbols.c.id).where(symbols.c.symbol_l18==symbol(l18))).scalar_one_or_none()
            if sid is None:raise HTTPException(404,'Symbol not found')
        def generate():
            stream=io.StringIO();writer=csv.writer(stream)
            fields=['date_shamsi','price_first','price_max','price_min','price_close','price_last','volume','value','source']
            writer.writerow(fields);yield '\ufeff'+stream.getvalue();stream.seek(0);stream.truncate(0)
            with engine.connect() as conn:
                rows=conn.execution_options(stream_results=True).execute(select(history).where(history.c.symbol_id==sid).order_by(history.c.date_shamsi.desc())).mappings()
                for r in rows:
                    writer.writerow([r[k] for k in fields]);yield stream.getvalue();stream.seek(0);stream.truncate(0)
        return StreamingResponse(generate(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="stock-history.csv"'})

    @router.get('/api/datasets',dependencies=[Depends(read_auth)])
    def dataset_catalog():return {'items':[{'id':name,'columns':[c.name for c in table.c]} for name,table in TABLES.items()]}

    return router
