"""Descriptive historical activity only; never treats unknown adjusted prices as returns."""
from pathlib import Path
import json,hashlib,argparse
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
NAMES={'S_Mobarakeh.Steel.csv':'foolad_candidate','Iran.Khodro.csv':'khodro_candidate','S_I..N..C..Ind..csv':'fameli_candidate'}

def analyze(source_dir,out):
    frames={};audits=[]
    for spec in json.loads((ROOT/'external_sources.json').read_text()):
        p=source_dir/spec['path'];raw=p.read_bytes();gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if gitsha!=spec['git_blob_sha']:raise ValueError('Source bytes changed: '+p.name)
        d=pd.read_csv(p);d.columns=[c.strip('<>') for c in d.columns]
        d['date']=pd.to_datetime(d.DTYYYYMMDD.astype(str),format='%Y%m%d');d=d.sort_values('date').set_index('date')
        valid=(d[['FIRST','HIGH','LOW','LAST','VALUE','VOL','OPENINT']]>0).all(axis=1)&(d.HIGH>=d.LOW)&d.FIRST.between(d.LOW,d.HIGH)&d.LAST.between(d.LOW,d.HIGH)
        sym=NAMES[p.name]
        audits.append(dict(file=p.name,symbol=sym,rows=len(d),start=str(d.index[0].date()),end=str(d.index[-1].date()),invalid=int((~valid).sum()),
                           duplicates=int(d.index.duplicated().sum()),sha256=hashlib.sha256(raw).hexdigest(),git_blob_sha=gitsha,adjustment_verified=False,stable_identity_verified=False))
        frames[sym]=d[valid]
    common=None
    for d in frames.values():common=d.index if common is None else common.intersection(d.index)
    values=pd.DataFrame({s:d.reindex(common).VALUE for s,d in frames.items()});shares=values.div(values.sum(axis=1),axis=0)
    annual=[];monthly=[]
    for year,ids in shares.groupby(shares.index.year).groups.items():
        for sym in shares:
            d=frames[sym].loc[ids]
            annual.append(dict(year=year,symbol=sym,n=len(d),activity_share=float(shares.loc[ids,sym].mean()),
               median_value_per_trade_rial=float((d.VALUE/d.OPENINT).median()),
               single_price_fraction=float(d.HIGH.eq(d.LOW).mean()),
               intraday_positive_fraction=float(d.LAST.gt(d.FIRST).mean()),
               median_intraday_range=float((d.HIGH/d.LOW-1).median()),median_trades=float(d.OPENINT.median())))
    for month,ids in shares.groupby(shares.index.to_period('M')).groups.items():
        for sym in shares:monthly.append(dict(month=str(month),symbol=sym,n=len(ids),activity_share=float(shares.loc[ids,sym].mean())))
    pd.DataFrame(audits).to_csv(out/'external_history_audit.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'external_activity_yearly.csv',index=False)
    pd.DataFrame(monthly).to_csv(out/'external_activity_monthly.csv',index=False)
    shares.to_csv(out/'external_activity_daily.csv')
    summary=dict(common_observations=len(common),start=str(common.min().date()),end=str(common.max().date()),
        interpretation='Aggregate activity among three file-name-mapped candidates; not trader identity, net money flow or adjusted return',
        raw_redistribution=False,source='alireza-jafari/DeepNet-dataset@860369ca5b702a03af1851d9fc2e590818f82fea')
    (out/'external_behavior_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
    print(pd.DataFrame(annual).pivot(index='year',columns='symbol',values='activity_share').tail(8).to_string())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'results');a=p.parse_args();analyze(a.input,a.output)
