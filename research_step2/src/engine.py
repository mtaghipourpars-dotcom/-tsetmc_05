"""Research-only adaptive trading. Daily proxies never certify order execution."""
import sys, json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'research_step1'/'src'))
from run import load, GOLD, EQUITY, DEFENSIVE, NAMES

FEATURES=['r3','relative_activity','last_first','location','overhang_change','group_share_change','stress']
FAMILIES=['repair','relay','supply_relief']

def build_features(frames,days,cfg):
    c=pd.DataFrame({s:d.reindex(days).CLOSE for s,d in frames.items()})
    v=pd.DataFrame({s:d.reindex(days).VALUE for s,d in frames.items()})
    groups={'gold':GOLD,'equity':EQUITY,'income':[DEFENSIVE]}
    group_value=pd.DataFrame({g:v[syms].sum(axis=1) for g,syms in groups.items()})
    share=group_value.div(group_value.sum(axis=1),axis=0)
    ret=c.pct_change(fill_method=None)
    group_returns=pd.DataFrame({g:ret[syms].mean(axis=1) for g,syms in groups.items()})
    r3=c.pct_change(3,fill_method=None)
    both_down=(group_returns.gold<0)&(group_returns.equity<0)
    gap=days.to_series().diff().dt.days.gt(7).rolling(10,min_periods=1).max().astype(bool)
    rows=[];L=cfg['lookback']
    for sym,d0 in frames.items():
        if sym==DEFENSIVE:continue
        d=d0.reindex(days);grp='gold' if sym in GOLD else 'equity'
        activity=d.VALUE/d.VALUE.shift(1).rolling(20,min_periods=15).median()
        loc=(d.LAST-d.LOW)/(d.HIGH-d.LOW).replace(0,np.nan)
        over=[]
        for i in range(len(d)):
            h=d.iloc[max(0,i-20):i]
            over.append(float((h.VOL*(h.CLOSE>d.CLOSE.iloc[i])).sum()/h.VOL.sum()) if len(h)>=15 and h.VOL.sum()>0 else np.nan)
        over=pd.Series(over,index=days);delta=over.diff()
        f=pd.DataFrame(dict(r3=r3[sym],relative_activity=np.log(activity.clip(.01,100)),last_first=d.LAST/d.FIRST-1,
              location=loc,overhang=over,overhang_change=delta,group_share=share[grp],
              group_share_change=share[grp]-share[grp].shift(3),stress=both_down.astype(float),
              capacity=cfg['participation']*d.VALUE.shift(1).rolling(20,min_periods=20).min(),
              gap=gap,group=grp,corporate_unknown=d.corporate_unknown),index=days)
        q=lambda s,p:s.shift(1).rolling(L,min_periods=30).quantile(p)
        # Adapt thresholds only from past observations; economic families remain fixed.
        repair=(f.r3<0)&(f.relative_activity>q(f.relative_activity,.6))&(f.last_first>0)&(f.location>.5)
        relay=(f.group_share_change>q(f.group_share_change,.75))&(group_returns[grp]>0)&(f.last_first>0)&(f.r3<q(f.r3,.8))
        relief=(f.overhang_change<q(f.overhang_change,.25))&(f.r3<q(f.r3,.6))&(f.relative_activity>q(f.relative_activity,.5))&(f.last_first>0)
        simple=(f.r3<0)&(f.last_first>0)
        momentum=(f.r3>0)&(f.r3>q(f.r3,.75))
        for i,dt in enumerate(days):
            if i<cfg['warmup']:continue
            regime='joint_stress' if both_down.iloc[i] else ('gold_lead' if group_returns.gold.iloc[i]>group_returns.equity.iloc[i] else 'equity_lead')
            row={'i':i,'date':str(dt.date()),'symbol':sym,'group':grp,'regime':regime,
                 'gap':bool(f.gap.iloc[i]),'corporate_unknown':bool(f.corporate_unknown.iloc[i]),
                 'single':bool(d.single.iloc[i]),'capacity':float(f.capacity.iloc[i]),
                 'q_activity60':float(q(f.relative_activity,.6).iloc[i]),
                 'q_share75':float(q(f.group_share_change,.75).iloc[i])}
            row.update({k:float(f[k].iloc[i]) for k in FEATURES+['group_share','overhang']})
            row.update({k:bool(mask.iloc[i]) for k,mask in [('repair',repair),('relay',relay),('supply_relief',relief),('simple',simple),('momentum',momentum)]})
            rows.append(row)
    panel=pd.DataFrame(rows)
    return panel,group_value,share,group_returns

def safety(row,days,cfg):
    if row['gap'] or row['corporate_unknown'] or row['single']:return False,'data_gap_corporate_or_single_price'
    if row['regime']=='joint_stress':return False,'joint_market_stress'
    change=pd.Timestamp(cfg['policy_change_reported'])
    since=np.flatnonzero(days>=change)
    if row['group']=='equity' and len(since) and int(since[0])<=row['i']<int(since[0])+cfg['post_change_pause_sessions']:
        return False,'reported_rule_change_quarantine'
    if not all(np.isfinite(row[k]) for k in FEATURES):return False,'missing_features'
    return True,''

def xvector(row,h,context=True):
    x=np.array([1.,row['r3']/.05,row['relative_activity'],row['last_first']/.02,
                row['location']-.5,row['overhang_change'],row['group_share_change']/.1,
                float(row['group']=='gold') if context else 0.,h/10.],dtype=float)
    return np.clip(x,-4,4)

def shadow_outcome(frames,days,row,h,capital,fee,slip,part,delay=0,fill=1.,cash_wait=2):
    """Construct future labels offline with explicit maturity; never expose before maturity."""
    i=row['i'];entry_i=i+1;sym=row['symbol'];d=frames[sym]
    if entry_i>=len(days):return None
    e=d.loc[days[entry_i]];px=float(e.FIRST)*(1+slip);qty=math.floor(capital/(px*(1+fee)));notional=qty*px
    u=int(hashlib.sha256((str(days[entry_i])+sym).encode()).hexdigest()[:8],16)/0xffffffff
    base=dict(signal_i=i,entry_i=entry_i,symbol=sym,family=row['family'],h=h,regime=row['regime'],group=row['group'],x=xvector(row,h).tolist())
    if qty<=0 or e.single or notional>min(row['capacity']*part/.01,part*float(e.VALUE)) or u>=fill:
        return dict(**base,maturity_i=entry_i,exit_i=None,net_return=0.,utility=-.001,filled=False,delay_sessions=0,mae=0.)
    cost=notional*(1+fee);remaining=qty;proceeds=0.;due=entry_i+h+delay;mae=0.;last_exit=None
    for j in range(entry_i,len(days)):
        r=d.loc[days[j]];mae=min(mae,float(r.LOW)/px-1)
        if j<due or r.single:continue
        sp=float(r.FIRST)*(1-slip);n=min(remaining,math.floor(part*float(r.VALUE)/sp))
        if n<=0:continue
        proceeds+=n*sp*(1-fee);remaining-=n
        if remaining==0:last_exit=j;break
    if remaining:return None # right-censored labels are never called wins or supplied to learner
    nr=proceeds/cost-1;held=last_exit-entry_i
    utility=(nr+.25*mae-.001*max(0,held-h))/max(1,held+cash_wait)
    return dict(**base,maturity_i=last_exit,exit_i=last_exit,net_return=nr,utility=utility,filled=True,delay_sessions=max(0,held-h),mae=mae)

class Learner:
    def __init__(self,cfg,context=True,forget=True):
        self.cfg=cfg;self.context=context;self.forget=forget;self.training=[];self.last_update=-1;self.cache=None
    def add_matured(self,records,i):
        assert all(r['maturity_i']<=i for r in records),'Future reward leaked'
        self.training.extend(records);self.last_update=i;self.cache=None
    def score(self,row,h,i):
        eligible=[r for r in self.training if r['maturity_i']<=i and i-r['maturity_i']<=360]
        if len(eligible)<self.cfg['min_labels']:return None
        blocks=len({r['signal_i']//10 for r in eligible})
        if blocks<self.cfg['min_blocks']:return None
        if self.cache is not None and self.cache[0]==i:beta=self.cache[1]
        else:
            X=np.array([r['x'] for r in eligible]);y=np.array([r['utility'] for r in eligible]);age=np.array([i-r['maturity_i'] for r in eligible])
            if not self.context:X[:,7]=0
            w=np.exp2(-age/self.cfg['half_life']) if self.forget else np.ones(len(age))
            # One day with many correlated symbols cannot contribute unlimited evidence.
            counts={}
            for r in eligible:counts[r['signal_i']]=counts.get(r['signal_i'],0)+1
            w=w/np.array([counts[r['signal_i']] for r in eligible])
            A=X.T@(w[:,None]*X)+self.cfg['ridge']*np.eye(X.shape[1])
            beta=np.clip(np.linalg.solve(A,X.T@(w*y)),-.02,.02);self.cache=(i,beta)
        pred=float(xvector(row,h,self.context)@beta)
        specialists=[r for r in eligible if r['family']==row['family'] and r['h']==h and (not self.context or r['regime']==row['regime'])]
        if len(specialists)<5:return None
        sw=np.exp2(-np.array([i-r['maturity_i'] for r in specialists])/self.cfg['half_life']) if self.forget else np.ones(len(specialists))
        sy=np.array([r['utility'] for r in specialists]);mean=float(np.average(sy,weights=sw))
        b=len({r['signal_i']//10 for r in specialists})
        shrink=b/(b+10);estimated=.5*pred+.5*shrink*mean
        spread=float(np.sqrt(np.average((sy-mean)**2,weights=sw)))
        penalty=spread/math.sqrt(max(1,b))
        return dict(score=estimated-penalty,predicted_utility=estimated,uncertainty_penalty=penalty,
             family_samples=len(specialists),blocks=b,train_max_maturity=max(r['maturity_i'] for r in eligible),beta=beta.tolist())

def simulate(frames,days,panel,labels,cfg,mode,capital,fee=None,slip=None,part=None,delay=0,fill=1.):
    fee=cfg['fee'] if fee is None else fee;slip=cfg['slippage'] if slip is None else slip;part=cfg['participation'] if part is None else part
    learner=Learner(cfg,context=mode!='adaptive_no_context',forget=mode!='adaptive_no_forgetting')
    byday={i:g.to_dict('records') for i,g in panel.groupby('i')};matures={}
    for r in labels:matures.setdefault(r['maturity_i'],[]).append(r)
    cash=float(capital);unsettled=[];pos=None;pending=None;equity=[];orders=[];trades=[];decisions=[];params=[];blocked=0
    total_costs=0.;turnover=0.;pnl_closed=0.;epoch=0
    for i,dt in enumerate(days):
        for amount,due in unsettled.copy():
            if i>=due:cash+=amount;unsettled.remove((amount,due))
        if pos and i>=pos['due']+delay:
            row=frames[pos['symbol']].loc[dt];px=float(row.FIRST)*(1-slip)
            n=0 if row.single else min(pos['remaining'],math.floor(part*float(row.VALUE)/px))
            if n:
                gross=n*px;net=gross*(1-fee);total_costs+=gross*fee;turnover+=gross;pos['proceeds']+=net;pos['remaining']-=n
                unsettled.append((net,i+cfg['cash_wait']))
                status='FILLED' if pos['remaining']==0 else 'PARTIAL'
                orders.append(dict(i=i,date=str(dt.date()),symbol=pos['symbol'],side='SELL',status=status,qty=n,price=px))
                if pos['remaining']==0:
                    pnl=pos['proceeds']-pos['cost'];pnl_closed+=pnl
                    trades.append(dict(symbol=pos['symbol'],family=pos['family'],h=pos['h'],signal_date=pos['signal_date'],entry=pos['entry'],exit=str(dt.date()),
                         net_return=pos['proceeds']/pos['cost']-1,pnl_rial=pnl,held_sessions=i-pos['entry_i'],delay_sessions=i-pos['due'],qty=pos['qty'],mae=pos['mae']))
                    pos=None
            else:
                blocked+=1;orders.append(dict(i=i,date=str(dt.date()),symbol=pos['symbol'],side='SELL',status='QUEUED',qty=0,price=px))
        if pending and i==pending['execute_i']:
            assert pos is None and not unsettled
            sym=pending['symbol'];row=frames[sym].loc[dt];px=float(row.FIRST)*(1+slip);q=math.floor(cash/(px*(1+fee)))
            gross=q*px;u=int(hashlib.sha256((str(dt)+sym).encode()).hexdigest()[:8],16)/0xffffffff
            cap=min(pending['capacity']*part/.01,part*float(row.VALUE))
            ok=q>0 and not row.single and gross<=cap and u<fill
            orders.append(dict(i=i,date=str(dt.date()),symbol=sym,side='BUY',status='FILLED' if ok else 'CANCELLED',qty=q if ok else 0,price=px))
            if ok:
                cost=gross*(1+fee);cash-=cost;total_costs+=gross*fee;turnover+=gross
                pos=dict(symbol=sym,qty=q,remaining=q,cost=cost,proceeds=0.,family=pending['family'],h=pending['h'],due=i+pending['h'],entry_i=i,
                         entry=str(dt.date()),signal_date=pending['date'],buy_price=px,mae=0.)
            pending=None
        if pos:
            rr=frames[pos['symbol']].loc[dt];pos['mae']=min(pos['mae'],float(rr.LOW)/pos['buy_price']-1)
            marked=pos['remaining']*float(rr.CLOSE)
        else:marked=0.
        eq=cash+sum(u[0] for u in unsettled)+marked
        equity.append(dict(i=i,date=str(dt.date()),equity=eq,free_cash=cash,unsettled_cash=sum(u[0] for u in unsettled),position_value=marked,symbol=pos['symbol'] if pos else ''))
        assert cash>=-1e-4
        if i and (dt-days[i-1]).days>21:
            learner=Learner(cfg,context=mode!='adaptive_no_context',forget=mode!='adaptive_no_forgetting');epoch=i
        if i in matures:learner.add_matured([r for r in matures[i] if r['signal_i']>=epoch],i)
        if pos or pending or unsettled or i>=len(days)-12:continue
        candidates=[];reject=[]
        for row in byday.get(i,[]):
            safe,reason=safety(row,days,cfg)
            if not safe:reject.append(reason);continue
            if cash/(1+fee)>row['capacity']*part/.01:reject.append('insufficient_full_position_capacity');continue
            if mode.startswith('adaptive'):
                for family in FAMILIES:
                    if not row[family]:continue
                    for h in cfg['horizons']:
                        r=dict(row,family=family,h=h);sc=learner.score(r,h,i)
                        if sc is not None:
                            params.append(dict(i=i,date=row['date'],symbol=row['symbol'],family=family,h=h,**sc))
                            if sc['score']>0:candidates.append(dict(r,**sc))
            else:
                if row.get(mode,False):
                    rank=row['r3'] if mode=='momentum' else -row['r3']
                    candidates.append(dict(row,family=mode,h=5,score=rank))
        if candidates:
            best=sorted(candidates,key=lambda r:(-r['score'],r['symbol'],r['h']))[0]
            pending=dict(best,execute_i=i+1)
            orders.append(dict(i=i,date=str(dt.date()),symbol=best['symbol'],side='BUY',status='NEW',qty=0,price=None))
            decisions.append(dict(i=i,date=str(dt.date()),action='BUY_RESEARCH',symbol=best['symbol'],family=best['family'],h=best['h'],score=best['score']))
        else:decisions.append(dict(i=i,date=str(dt.date()),action='CASH',symbol='',family='',h=None,score=None,reason=';'.join(sorted(set(reject))) if reject else 'no_positive_mature_evidence_or_signal'))
    curve=pd.DataFrame(equity);tr=pd.DataFrame(trades);od=pd.DataFrame(orders);dc=pd.DataFrame(decisions);pa=pd.DataFrame(params)
    open_pnl=(pos['proceeds']+marked-pos['cost']) if pos else 0.
    assert abs(curve.equity.iloc[-1]-capital-pnl_closed-open_pnl)<max(.1,capital*1e-9)
    return curve,tr,od,dc,pa,dict(open_final=pos is not None,total_costs=total_costs,turnover=turnover/capital,blocked_exit_sessions=blocked,
                                  final_free_cash=cash,final_unsettled=sum(u[0] for u in unsettled),open_pnl=open_pnl)

def metrics(curve,tr,capital=None):
    if not len(curve):return {}
    vals=curve.equity.to_numpy();initial=float(capital or vals[0]);peak=np.maximum.accumulate(np.r_[initial,vals])[1:]
    dd=vals/peak-1;r=np.diff(np.r_[initial,vals])/np.r_[initial,vals][:-1]
    streak=longest=0
    for q in dd<0:streak=streak+1 if q else 0;longest=max(longest,streak)
    pnl=tr.pnl_rial if len(tr) else pd.Series(dtype=float);w=pnl[pnl>0];l=pnl[pnl<0]
    return dict(net_return=vals[-1]/initial-1,max_drawdown=float(dd.min()),drawdown_sessions=longest,trades=len(tr),
        win_rate=float((pnl>0).mean()) if len(tr) else None,payoff=float(w.mean()/-l.mean()) if len(w) and len(l) else None,
        exposure=float((curve.position_value>0).mean()),mean_hold=float(tr.held_sessions.mean()) if len(tr) else None,
        worst_trade=float(tr.net_return.min()) if len(tr) else None,mean_daily_return=float(r.mean()),
        delayed_trade_fraction=float((tr.delay_sessions>0).mean()) if len(tr) else None)

def make_labels(frames,days,panel,cfg,capital,fee,slip,part,delay=0,fill=1.):
    labels=[];censored=0
    for row in panel.to_dict('records'):
        safe,_=safety(row,days,cfg)
        if not safe:continue
        for fam in FAMILIES:
            if not row[fam]:continue
            for h in cfg['horizons']:
                label=shadow_outcome(frames,days,dict(row,family=fam),h,capital,fee,slip,part,delay,fill,cfg['cash_wait'])
                if label is not None:labels.append(label)
                else:censored+=1
    return labels,censored

def run(data,out,cfg):
    out.mkdir(parents=True,exist_ok=True);frames,days=load(data,out)
    panel,values,share,gret=build_features(frames,days,cfg)
    panel.to_csv(out/'behavior_features.csv',index=False);values.to_csv(out/'group_trading_value.csv');share.to_csv(out/'group_activity_share.csv');gret.to_csv(out/'group_returns.csv')
    rows=[];label_stats=[]
    for cap in cfg['capitals_rial']:
        scenarios=[('base',cfg['fee'],cfg['slippage'],cfg['participation'],0,1.)]
        if cap==cfg['capitals_rial'][0]:scenarios += [('low_cost',.0005,.0005,.01,0,1.),('high_cost',.003,.002,.01,0,1.),('stress',.003,.002,.003,3,.5)]
        for scenario,fee,slip,part,delay,fill in scenarios:
            labels,censored=make_labels(frames,days,panel,cfg,cap,fee,slip,part,delay,fill)
            label_stats.append(dict(capital_rial=cap,scenario=scenario,labels=len(labels),censored=censored,entry_failures=sum(not r['filled'] for r in labels)))
            modes=FAMILIES+['simple','momentum','adaptive','adaptive_no_context','adaptive_no_forgetting'] if scenario=='base' and cap==cfg['capitals_rial'][0] else ['adaptive']
            for mode in modes:
                curve,tr,od,dc,pa,extra=simulate(frames,days,panel,labels,cfg,mode,cap,fee,slip,part,delay,fill)
                key=f'{mode}_{cap}_{scenario}'
                for period in ['ALL','2024','2025','2026']:
                    mask=np.ones(len(curve),dtype=bool) if period=='ALL' else pd.to_datetime(curve.date).dt.year.eq(int(period)).to_numpy()
                    sub=curve[mask];tt=tr if period=='ALL' else tr[pd.to_datetime(tr.exit).dt.year.eq(int(period))] if len(tr) else tr
                    if len(sub):
                        firstidx=sub.index[0];initial=cap if firstidx==0 else float(curve.loc[firstidx-1,'equity'])
                        rows.append(dict(run=key,mode=mode,capital_rial=cap,scenario=scenario,period=period,**metrics(sub,tt,initial),**extra))
                if cap==cfg['capitals_rial'][0] and scenario=='base':
                    curve.to_csv(out/f'{mode}_equity.csv',index=False);tr.to_csv(out/f'{mode}_trades.csv',index=False)
                    od.to_csv(out/f'{mode}_orders.csv',index=False);dc.to_csv(out/f'{mode}_decisions.csv',index=False)
                    if len(pa):
                        pa['beta']=pa.beta.apply(json.dumps);pa.to_csv(out/f'{mode}_learning_log.csv',index=False)
                if mode=='adaptive' and cap==cfg['capitals_rial'][0] and scenario=='base':
                    clean=[{k:v for k,v in r.items() if k!='x'} for r in labels]
                    pd.DataFrame(clean).to_csv(out/'matured_shadow_labels.csv',index=False)
    result=pd.DataFrame(rows);result.to_csv(out/'strategy_metrics.csv',index=False);pd.DataFrame(label_stats).to_csv(out/'label_quality.csv',index=False)
    summary=dict(input_commit=cfg['input_commit'],start=str(days[0].date()),end=str(days[-1].date()),common_observations=len(days),
                 feature_rows=len(panel),status='RESEARCH_ONLY',learning_implemented=True,live_eligible=False,
                 missing=['historical_instrument_rules','official_fee_versions','adjustment_lineage','historical_orderbook','participant_level_flows'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(result[(result.period=='2026')][['mode','capital_rial','scenario','net_return','max_drawdown','trades','exposure']].to_string(index=False))
    return frames,days,panel,values,share,gret,result
