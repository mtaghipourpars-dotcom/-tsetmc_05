from pathlib import Path
import json,html
import numpy as np
import pandas as pd
from engine import GOLD,EQUITY,DEFENSIVE,NAMES

def analyze(data,out,frames,days,panel,values,share,returns,result):
    rows=[]
    for period,ix in share.groupby(share.index.to_period('M')).groups.items():
        dates=pd.DatetimeIndex(ix)
        for grp in share:
            syms=GOLD if grp=='gold' else EQUITY if grp=='equity' else [DEFENSIVE]
            singles=np.mean([frames[s].reindex(dates).single.mean() for s in syms])
            rows.append(dict(month=str(period),group=grp,observations=len(dates),activity_share=float(share.loc[dates,grp].mean()),
                mean_daily_return=float(returns.loc[dates,grp].mean()),volatility=float(returns.loc[dates,grp].std()),single_price_fraction=singles,
                trading_value_rial=float(values.loc[dates,grp].sum())))
    monthly=pd.DataFrame(rows);monthly.to_csv(out/'behavior_monthly.csv',index=False)
    annual=[]
    for yr,sub in share.groupby(share.index.year):
        ids=sub.index
        annual.append(dict(year=yr,n=len(ids),gold_share=float(sub.gold.mean()),equity_share=float(sub.equity.mean()),income_share=float(sub.income.mean()),
              gold_equity_corr=float(returns.loc[ids,'gold'].corr(returns.loc[ids,'equity'])),
              joint_down_fraction=float(((returns.loc[ids,'gold']<0)&(returns.loc[ids,'equity']<0)).mean()),
              dominant_activity_switches=int(sub.idxmax(axis=1).ne(sub.idxmax(axis=1).shift()).iloc[1:].sum())))
    pd.DataFrame(annual).to_csv(out/'behavior_yearly.csv',index=False)
    assets=[]
    allv=pd.DataFrame({s:frames[s].reindex(days).VALUE for s in frames})
    shares=allv.div(allv.sum(axis=1),axis=0)
    for yr,ss in shares.groupby(shares.index.year):
        for sym in shares:
            dd=frames[sym].reindex(ss.index)
            assets.append(dict(year=yr,symbol=sym,share=float(ss[sym].mean()),single_price_fraction=float(dd.single.mean()),
                 mean_trade_size_rial=float((dd.VALUE/dd.OPENINT).median()),
                 activity_return_corr=float(dd.VALUE.pct_change(fill_method=None).corr(dd.CLOSE.pct_change(fill_method=None)))))
    pd.DataFrame(assets).to_csv(out/'asset_behavior_yearly.csv',index=False)
    shifts=share.diff(3)
    shifts.assign(dominant=share.idxmax(axis=1),largest_shift=shifts.abs().max(axis=1)).to_csv(out/'activity_rotation_daily.csv')
    # Local prices/turnover prove aggregate activity, never identity-level fund transfers.
    norm=lambda x:x.replace('ي','ی').replace('ك','ک').replace('\u200c','').replace(' ','')
    wanted={norm(s):s for s in ['فملی','فولاد','خودرو','عیار','اهرم','کهربا','آلتون','موج','شتاب','توان','اعتماد']}
    selected=[];market=[]
    for p in sorted(data.glob('MarketWatch*.md')):
        date=p.stem.split('-',1)[1].replace('_','/')
        lines=[[v.strip() for v in l.split('|')[1:-1]] for l in p.read_text().splitlines() if l.startswith('|')][4:]
        parsed=[]
        for row in lines:
            try:vals=[float(x.replace(',','')) for x in row[2:]]
            except (ValueError,TypeError):continue
            if len(vals)!=13:continue
            record=dict(jalali_date=date,symbol=row[0],name=row[1],trades=vals[0],volume=vals[1],value=vals[2],prior=vals[3],first=vals[4],last=vals[5],close=vals[8],low=vals[11],high=vals[12])
            if norm(row[0]) in wanted:record['selected_name']=wanted[norm(row[0])];selected.append(record)
            parsed.append(record)
        # Broad file contains mixed instruments; do not call this equity-market breadth.
        market.append(dict(jalali_date=date,rows=len(parsed),positive_price_rows=sum(r['close']>r['prior'] for r in parsed),
             negative_price_rows=sum(r['close']<r['prior'] for r in parsed),single_price_rows=sum(r['high']==r['low'] for r in parsed),
             classification='mixed_instrument_snapshot_not_equity_breadth'))
    pd.DataFrame(selected).to_csv(out/'selected_symbols_10sessions.csv',index=False);pd.DataFrame(market).to_csv(out/'snapshot_scope.csv',index=False)
    labels=pd.read_csv(out/'matured_shadow_labels.csv')
    stats=[]
    for keys,g in labels.groupby(['family','h']):
        filled=g[g.filled]
        stats.append(dict(family=keys[0],h=int(keys[1]),labels=len(g),filled=len(filled),fill_fraction=float(g.filled.mean()),
              mean_conditional_return=float(filled.net_return.mean()),median_conditional_return=float(filled.net_return.median()),
              conditional_win_rate=float((filled.net_return>0).mean()),mean_utility=float(g.utility.mean()),
              notice='overlapping_shadow_opportunities_not_portfolio_returns'))
    pd.DataFrame(stats).to_csv(out/'hypothesis_diagnostics.csv',index=False)
    bootstrap=[];rng=np.random.default_rng(731)
    for mode in ['adaptive','repair','relay','supply_relief','simple','momentum']:
        curve=pd.read_csv(out/f'{mode}_equity.csv');r=curve.equity.pct_change().fillna(0)
        rr=r[pd.to_datetime(curve.date).dt.year.eq(2026)].to_numpy();n=len(rr)
        draws=[]
        for _ in range(1000):
            starts=rng.integers(0,n,size=int(np.ceil(n/10)));sample=np.concatenate([rr[(np.arange(10)+k)%n] for k in starts])[:n];draws.append(sample.mean())
        lo,hi=np.quantile(draws,[.025,.975]);bootstrap.append(dict(mode=mode,year=2026,mean_daily=float(rr.mean()),ci_low=lo,ci_high=hi,block=10,iterations=1000,multiple_testing_adjusted=False))
    pd.DataFrame(bootstrap).to_csv(out/'block_bootstrap_2026.csv',index=False)
    # Paired mark-to-market returns share the same calendar; still not same risk exposure.
    eqs={m:pd.read_csv(out/f'{m}_equity.csv').set_index('date').equity.pct_change().fillna(0) for m in ['adaptive','repair','relay','supply_relief','simple','momentum']}
    paired=[]
    for m in ['repair','relay','supply_relief','simple','momentum']:
        diff=(eqs['adaptive']-eqs[m]);rr=diff[pd.to_datetime(diff.index).year==2026].to_numpy();n=len(rr);draws=[]
        for _ in range(1000):
            starts=rng.integers(0,n,size=int(np.ceil(n/10)));draws.append(np.concatenate([rr[(np.arange(10)+k)%n] for k in starts])[:n].mean())
        lo,hi=np.quantile(draws,[.025,.975]);paired.append(dict(comparison='adaptive_minus_'+m,mean_daily_difference=rr.mean(),ci_low=lo,ci_high=hi))
    pd.DataFrame(paired).to_csv(out/'paired_differences_2026.csv',index=False)
    # Passive price references only. Unknown adjustments/distributions disallow total-return claims.
    passive=[]
    for yr in [2024,2025,2026]:
        for sym,d in frames.items():
            p=d.reindex(days).CLOSE.loc[str(yr)];nav=p/p.iloc[0]
            passive.append(dict(year=yr,symbol=sym,price_change=float(nav.iloc[-1]-1),max_drawdown=float((nav/nav.cummax()-1).min()),costs_included=False,adjustment_verified=False))
        passive.append(dict(year=yr,symbol='CASH',price_change=0,max_drawdown=0,costs_included=True,adjustment_verified=True))
    pd.DataFrame(passive).to_csv(out/'passive_price_references.csv',index=False)
    charts(out,share,result)
    (out/'behavior_summary.json').write_text(json.dumps(dict(yearly=annual,monthly_observations=len(monthly),selected_snapshot_rows=len(selected),participant_identity_inferred=False),indent=2))
    print('Behavior summary:',json.dumps(annual,ensure_ascii=False))

def charts(out,share,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','font.size':10})
    fig,ax=plt.subplots(figsize=(9,3.4));s=share.resample('ME').mean();ax.stackplot(s.index,s.gold,s.equity,s.income,labels=['Gold (3 funds)','Leveraged equity (4)','Fixed income (1)'],colors=['#d2a637','#327f9e','#8f9f9b'])
    ax.set_ylim(0,1);ax.set_ylabel('Share of trading value within selected 8');ax.legend(loc='upper left',fontsize=8);fig.tight_layout();fig.savefig(out/'activity_share.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.4))
    for mode in ['adaptive','repair','relay','supply_relief','simple','momentum']:
        d=pd.read_csv(out/f'{mode}_equity.csv');ax.plot(pd.to_datetime(d.date),d.equity/d.equity.iloc[0],label=mode,linewidth=1.3)
    ax.set_ylabel('Research marked equity / initial');ax.legend(ncol=3,fontsize=8);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'research_equity.svg');plt.close(fig)
