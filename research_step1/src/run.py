"""Exploratory daily proxy. All price fills and capacity are assumptions."""
from pathlib import Path
import argparse, hashlib, json, math, html
import numpy as np
import pandas as pd
from audit_snapshots import audit_snapshots

ROOT = Path(__file__).resolve().parents[1]
GOLD = ['Ayar', 'Kahroba', 'Alton']
EQUITY = ['CharismaAhromi.ETF', 'Moj.ETF-LR', 'Shetab.ETF', 'Tavan.ETF-LR']
DEFENSIVE = 'Etemad.Parsian.ETF'
NAMES = dict(zip(GOLD+EQUITY+[DEFENSIVE], ['عیار','کهربا','آلتون','اهرم','موج','شتاب','توان','اعتماد پارسیان']))

def table(path):
    rows = [[v.strip() for v in line.split('|')[1:-1]] for line in path.read_text().splitlines() if line.startswith('|')]
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows[2:], columns=[s.strip('<>') for s in rows[0]])

def load(data, out):
    frames, audit, manifests = {}, [], []
    snapshots = []
    for p in sorted(data.glob('*')):
        if not p.is_file(): continue
        manifests.append(dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
        if p.suffix != '.md': continue
        if 'MarketWatch' in p.name:
            rows = [[v.strip() for v in l.split('|')[1:-1]] for l in p.read_text().splitlines() if l.startswith('|')]
            body = rows[4:]
            valid = [r for r in body if len(r)==15 and r[0]]
            snapshots.append(dict(file=p.name,rows=len(valid),distinct_symbols=len(set(r[0] for r in valid)),columns=15,order_book=False))
            continue
        d=table(p)
        if 'DTYYYYMMDD' not in d: continue
        sym=d.TICKER.iloc[0].strip()
        for col in d.columns.difference(['TICKER','PER']):
            d[col]=pd.to_numeric(d[col].str.replace(',','',regex=False),errors='coerce')
        d['date']=pd.to_datetime(d.DTYYYYMMDD.astype('Int64').astype(str),format='%Y%m%d',errors='coerce')
        dup=int(d.date.duplicated().sum())
        d=d.sort_values('date').set_index('date')
        invalid=(d[['FIRST','HIGH','LOW','CLOSE','LAST','VALUE','VOL']].isna().any(axis=1) |
                 (d[['FIRST','HIGH','LOW','CLOSE','LAST','VALUE','VOL']]<=0).any(axis=1) |
                 (d.HIGH<d.LOW) | (d.FIRST<d.LOW) | (d.FIRST>d.HIGH) |
                 (d.LAST<d.LOW) | (d.LAST>d.HIGH) | (d.CLOSE<d.LOW) | (d.CLOSE>d.HIGH))
        d['valid']=~invalid
        d['single']=d.HIGH.eq(d.LOW)
        vwap=d.VALUE/d.VOL
        audit.append(dict(symbol=sym,rows=len(d),start=str(d.index.min().date()),end=str(d.index.max().date()),duplicates=dup,
             invalid=int(invalid.sum()),single_price=int(d.single.sum()),
             open_equals_prior_close=int(d.OPEN.eq(d.CLOSE.shift()).sum()),comparisons=len(d)-1,
             close_jumps_20pct=int((d.CLOSE.pct_change(fill_method=None).abs()>.2).sum()),
             vwap_outside_range=int(((vwap<d.LOW*.999)|(vwap>d.HIGH*1.001)).sum()),max_gap_days=int(d.index.to_series().diff().dt.days.max())))
        if dup or d.index.isna().any(): raise ValueError(f'Duplicate/invalid dates: {sym}')
        # Unexplained >20% discontinuities: block fresh entries for 20 observations.
        d['corporate_unknown']=d.CLOSE.pct_change(fill_method=None).abs().gt(.2).rolling(20,min_periods=1).max().astype(bool)
        frames[sym]=d
    pd.DataFrame(audit).to_csv(out/'data_audit.csv',index=False)
    pd.DataFrame(snapshots).to_csv(out/'snapshot_audit.csv',index=False)
    (out/'source_manifest.json').write_text(json.dumps(manifests,indent=2))
    # Only actual shared valid observations. Omitted dates are reported, never zero-filled.
    all_days=sorted(set().union(*(set(d.index) for d in frames.values())))
    common=frames[next(iter(frames))].index
    for d in frames.values(): common=common.intersection(d.index[d.valid])
    common=common.sort_values()
    pd.DataFrame([dict(symbol=s,missing_union=len(set(all_days)-set(d.index)),excluded_from_common=len(d)-len(common)) for s,d in frames.items()]).to_csv(out/'calendar_gaps.csv',index=False)
    return frames, common

def features(frames, days):
    close=pd.DataFrame({s:d.reindex(days).CLOSE for s,d in frames.items()})
    first=pd.DataFrame({s:d.reindex(days).FIRST for s,d in frames.items()})
    last=pd.DataFrame({s:d.reindex(days).LAST for s,d in frames.items()})
    r=close.pct_change(fill_method=None)
    groups=pd.DataFrame({'gold':r[GOLD].mean(axis=1), 'equity':r[EQUITY].mean(axis=1)})
    corr=groups.gold.rolling(60,min_periods=60).corr(groups.equity)
    lag=close.pct_change(3,fill_method=None)
    scores=pd.DataFrame(np.nan,index=days,columns=close.columns)
    for members in (GOLD,EQUITY):
        condition=(lag[members].mean(axis=1)<0)&((last[members]>first[members]).mean(axis=1)>.5)
        for s in members:
            good=condition&(lag[s]<0)&(last[s]>first[s])&~frames[s].reindex(days).corporate_unknown
            scores.loc[good,s]=-lag.loc[good,s]
    scores.iloc[:60]=np.nan
    return close,groups,corr,scores

def simulate(frames, days, scores, corr, capital, hold=5, inverse=True, fee=.0015, slip=.001, participation=.01, delay=0, fill_fraction=1, cash_wait=2, start=0, end=None, benchmark=None):
    end=len(days) if end is None else end
    cash=float(capital); position=None; pending=None; ready=start
    ledger=[]; events=[]; curve=[]; last_price=0; fees=0.; turnover=0.; blocked=0
    for i in range(start,end):
        dt=days[i]; sold=False
        if position:
            sym=position['symbol']; row=frames[sym].loc[dt]; last_price=float(row.CLOSE)
            if i>=position['due']+delay:
                px=float(row.FIRST)*(1-slip)
                capacity=participation*float(row.VALUE)
                if row.valid and not row.single and position['qty']*px<=capacity:
                    proceeds=position['qty']*px*(1-fee); cash+=proceeds
                    sell_fee=position['qty']*px*fee; fees+=sell_fee;turnover+=position['qty']*px
                    ledger.append(dict(symbol=sym,signal_date=position['signal_date'],entry=position['entry'],exit=str(dt.date()),qty=position['qty'],
                         buy_price=position['buy_price'],sell_price=px,net_pnl=proceeds-position['cost'],net_return=proceeds/position['cost']-1,
                         held_sessions=i-position['entry_i'],exit_delay=i-position['due'],buy_fee=position['buy_fee'],sell_fee=sell_fee))
                    events.append(dict(date=str(dt.date()),symbol=sym,side='SELL',status='FILLED'))
                    position=None;ready=i+cash_wait; sold=True
                else:
                    blocked+=1;events.append(dict(date=str(dt.date()),symbol=sym,side='SELL',status='QUEUED',reason='assumed_capacity_or_single_price'))
        if pending and not position and i==pending['execute_i']:
            sym=pending['symbol'];row=frames[sym].loc[dt]
            px=float(row.FIRST)*(1+slip);qty=math.floor(cash/(px*(1+fee)))
            notional=qty*px
            deterministic=int(hashlib.sha256((str(dt)+sym).encode()).hexdigest()[:8],16)/0xffffffff
            capacity=min(pending['planned_capacity'],participation*float(row.VALUE))
            can_fill=(row.valid and not row.single and qty>0 and notional<=capacity and deterministic<fill_fraction)
            if can_fill:
                buy_fee=notional*fee;cost=notional+buy_fee;cash-=cost;fees+=buy_fee;turnover+=notional
                position=dict(symbol=sym,qty=qty,cost=cost,buy_price=px,buy_fee=buy_fee,entry=str(dt.date()),entry_i=i,due=i+hold,signal_date=pending['signal_date'])
                last_price=float(row.CLOSE)
            events.append(dict(date=str(dt.date()),symbol=sym,side='BUY',status='FILLED' if can_fill else 'CANCELLED',reason='' if can_fill else 'assumed_capacity_single_price_or_fill_stress'))
            pending=None
        if not position and pending is None and not sold and i>=ready and i>=start+10 and i<end-hold-delay-10:
            candidates=scores.iloc[i].dropna().sort_values(ascending=False)
            if benchmark is not None: candidates=pd.Series({benchmark:1.})
            if len(candidates) and (not inverse or pd.notna(corr.iloc[i]) and corr.iloc[i]<0):
                # Reject untradeable leaders before choosing the next eligible candidate.
                for sym in candidates.index:
                    history=frames[sym].loc[:dt].tail(20)
                    capacity=participation*float(history.VALUE.min())
                    if len(history)==20 and cash/(1+fee)<=capacity and not history.corporate_unknown.iloc[-1]:
                        pending=dict(symbol=sym,signal_date=str(dt.date()),execute_i=i+1,planned_capacity=capacity)
                        events.append(dict(date=str(dt.date()),symbol=sym,side='BUY',status='NEW')); break
        held_value=position['qty']*last_price if position else 0.
        eq=cash+held_value
        assert cash>=-1e-5 and eq>=0
        curve.append(dict(date=str(dt.date()),equity=eq,cash=cash,position_value=held_value,symbol=position['symbol'] if position else '',open_position=bool(position)))
    daily=pd.DataFrame(curve);tr=pd.DataFrame(ledger);ev=pd.DataFrame(events)
    vals=daily.equity.to_numpy();peak=np.maximum.accumulate(np.r_[capital,vals])[1:];under=vals<peak
    longest=run=0
    for u in under: run=run+1 if u else 0;longest=max(longest,run)
    ret=np.diff(np.r_[capital,vals])/np.r_[capital,vals][:-1]
    pnl=tr.net_pnl if len(tr) else pd.Series(dtype=float)
    wins=pnl[pnl>0];losses=pnl[pnl<0]
    realized=float(pnl.sum());open_pnl=(position['qty']*last_price-position['cost']) if position else 0
    assert abs((vals[-1]-capital)-(realized+open_pnl))<max(1,capital*1e-10)
    m=dict(net_return=vals[-1]/capital-1,max_drawdown=float((vals/peak-1).min()),drawdown_sessions=longest,
        trades=len(tr),win_rate=float((pnl>0).mean()) if len(pnl) else None,
        payoff=float(wins.mean()/(-losses.mean())) if len(wins) and len(losses) else None,
        profit_factor=float(wins.sum()/(-losses.sum())) if len(losses) else None,
        exposure=float(daily.open_position.mean()),turnover=turnover/capital,fees_rial=fees,
        mean_hold=float(tr.held_sessions.mean()) if len(tr) else None,exit_blocked_sessions=blocked,
        open_final=bool(position),free_cash_final=cash,marked_equity_final=vals[-1],open_pnl=open_pnl,
        cancelled_entries=int(((ev.side=='BUY')&(ev.status=='CANCELLED')).sum()) if len(ev) else 0,
        cagr=float((vals[-1]/capital)**(365.25/max(1,(days[end-1]-days[start]).days))-1),
        worst_trade=float(tr.net_return.min()) if len(tr) else None,mean_daily_return=float(ret.mean()),
        break_even_extra_cost_per_side_approx=(vals[-1]-capital)/turnover if turnover else None)
    return m,daily,tr,ev,ret

def block_ci(r, seed=173):
    rng=np.random.default_rng(seed);n=len(r);length=10;means=[]
    for _ in range(1000):
        starts=rng.integers(0,n,size=math.ceil(n/length))
        sample=np.concatenate([r[(np.arange(length)+i)%n] for i in starts])[:n]
        means.append(sample.mean())
    return [float(x) for x in np.quantile(means,[.025,.975])]

def main():
    a=argparse.ArgumentParser();a.add_argument('--data',type=Path,default=ROOT/'Data');args=a.parse_args()
    out=ROOT/'results';out.mkdir(exist_ok=True);cfg=json.loads((ROOT/'config.json').read_text())
    frames,days=load(args.data,out);crosscheck=audit_snapshots(args.data,frames,out);close,groups,corr,scores=features(frames,days)
    groups.assign(corr60=corr).to_csv(out/'group_returns_correlation.csv')
    correlations=[]
    for yr,g in groups.groupby(groups.index.year):
        correlations.append(dict(year=yr,n=len(g),correlation=g.gold.corr(g.equity)))
    correlations.append(dict(year='ALL',n=len(groups),correlation=groups.gold.corr(groups.equity)))
    pd.DataFrame(correlations).to_csv(out/'correlation_summary.csv',index=False)
    rows=[];cis=[]
    periods={'train':days<=cfg['train_end'],'validation':(days>cfg['train_end'])&(days<=cfg['validation_end']),'test':days>cfg['validation_end']}
    for period,mask in periods.items():
        ids=np.flatnonzero(mask)
        if len(ids)<80: continue
        start,end=int(ids[0]),int(ids[-1])+1
        for capital in cfg['capitals_rial']:
            for inv in (False,True):
                for hold in cfg['hold_sessions']:
                    scenarios=[('base',.0015,.001,.01,0,1.)]
                    if hold==5:
                        scenarios += [('low_cost',.0005,.0005,.01,0,1.),('high_cost',.003,.002,.01,0,1.),('stress',.003,.002,.003,3,.5)]
                    for scenario,fee,slip,part,delay,fill in scenarios:
                        m,d,t,e,r=simulate(frames,days,scores,corr,capital,hold,inv,fee,slip,part,delay,fill,start=start,end=end)
                        key=f'{period}_{capital}_{"inverse" if inv else "simple"}_{hold}_{scenario}'
                        rows.append(dict(run=key,period=period,capital_rial=capital,inverse=inv,hold=hold,scenario=scenario,**m))
                        if period=='test' and hold==5 and scenario=='base':
                            ci=block_ci(r);cis.append(dict(run=key,mean_daily_return=m['mean_daily_return'],ci_low=ci[0],ci_high=ci[1]))
                        if period=='test' and capital==cfg['capitals_rial'][0] and hold==5 and scenario in ('base','stress'):
                            d.to_csv(out/f'{key}_equity.csv',index=False);t.to_csv(out/f'{key}_trades.csv',index=False);e.to_csv(out/f'{key}_orders.csv',index=False)
        # A same-horizon always-reentering benchmark for each asset, with the same execution/cost assumptions.
        for sym in frames:
            m,*_=simulate(frames,days,scores,corr,cfg['capitals_rial'][0],hold=5,inverse=False,start=start,end=end,benchmark=sym)
            rows.append(dict(run=f'{period}_time_baseline_{sym}',period=period,capital_rial=cfg['capitals_rial'][0],inverse=False,hold=5,scenario='time_baseline',symbol=sym,**m))
        # Passive price benchmarks; distribution/adjustment unknown, explicitly price-only.
        for sym in frames:
            px=close[sym].iloc[start:end];nav=px/px.iloc[0];dd=nav/nav.cummax()-1
            rows.append(dict(run=f'{period}_passive_{sym}',period=period,scenario='passive_price_only',symbol=sym,net_return=nav.iloc[-1]-1,max_drawdown=dd.min(),exposure=1.))
        rows.append(dict(run=f'{period}_cash',period=period,scenario='cash',net_return=0.,max_drawdown=0.,exposure=0.))
    metrics=pd.DataFrame(rows);metrics.to_csv(out/'metrics.csv',index=False);pd.DataFrame(cis).to_csv(out/'block_bootstrap.csv',index=False)
    latest=[]
    dt=days[-1]
    for sym in frames:
        v=float(frames[sym].loc[:dt].tail(20).VALUE.min())*.01
        latest.append(dict(symbol=sym,name=NAMES[sym],as_of=str(dt.date()),close=float(close[sym].iloc[-1]),
              research_score=None if pd.isna(scores[sym].iloc[-1]) else float(scores[sym].iloc[-1]),
              assumed_capacity_rial=v,eligible_proxy=bool(pd.notna(scores[sym].iloc[-1])),
              corr60=float(corr.iloc[-1]),queue_verified=False))
    latest.sort(key=lambda x:(not x['eligible_proxy'],-(x['research_score'] or 0)))
    (out/'dashboard_snapshot.json').write_text(json.dumps(dict(as_of=str(dt.date()),real_position=None,
         predicted_profit=None,estimated_sale_date=None,alternatives=latest,live=False),ensure_ascii=False,indent=2))
    summary=dict(commit=cfg['snapshot_commit'],common_start=str(days[0].date()),common_end=str(days[-1].date()),common_sessions=len(days),
         corr_negative_share=float(corr.dropna().lt(0).mean()),corr_latest=float(corr.iloc[-1]),runs=len(metrics),snapshot_crosscheck=crosscheck,
         strict_executable_backtest='BLOCKED: historical limits/book/fees/settlement/adjustments not verified',
         paper_trading_approved=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    make_dashboard(latest,metrics,summary,out)
    print(json.dumps(summary,indent=2))
    print(metrics[(metrics.period=='test')&(metrics.hold==5)&(metrics.scenario.isin(['base','stress']))][['run','net_return','max_drawdown','trades','exposure','open_final']].to_string(index=False))

def make_dashboard(latest,metrics,summary,out):
    cells=''.join('<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in [r['name'],f"{r['close']:,.0f}",'واجد جانشین روزانه' if r['eligible_proxy'] else 'فاقد سیگنال',f"{r['assumed_capacity_rial']/10:,.0f}",'تأیید نشده'])+'</tr>' for r in latest)
    tests=metrics[(metrics.period=='test')&(metrics.scenario=='base')&(metrics.hold==5)]
    result=tests[['run','net_return','max_drawdown','trades','exposure']].to_html(index=False,float_format=lambda v:f'{v:.4f}')
    s=f'''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>گام اول پژوهش</title>
    <style>body{{font:16px Tahoma,sans-serif;background:#0f1925;color:#e5eef7;margin:0;padding:4vw}}main{{max-width:1200px;margin:auto}}h1{{font-size:28px}}section{{background:#1b2938;border-radius:16px;padding:24px;margin:20px 0;overflow:auto}}.badge{{color:#ffce70}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px;text-align:right;border-bottom:1px solid #41546a}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}p{{line-height:1.9}}small{{color:#aebfd1}}</style><main>
    <h1>تصمیم‌یار نوسان‌گیری | گام اول</h1><p class="badge">داده تاریخی تا {summary['common_end']} | سیگنال پژوهشی، بدون مجوز خرید</p>
    <div class="grid"><section>موقعیت واقعی<p>ثبت نشده</p><small>سود محقق‌شده و زمان خرید نامعلوم</small></section><section>فروش و سود پیش‌بینی‌شده<p>محاسبه معتبر موجود نیست</p><small>افق آزمون اصلی ۵ جلسه، نه وعده زمان فروش</small></section><section>اعتبار صف<p>تأیید نشده</p><small>داده دفتر سفارش موجود نیست</small></section></div>
    <section><h2>دارایی‌های منتخب</h2><p>ترتیب صرفاً امتیاز فرضیه روزانه است. ظرفیت، یک درصد کمترین ارزش ۲۰ روز گذشته و به تومان با فرض ریالی بودن منبع است.</p><table><tr><th>دارایی</th><th>قیمت منبع</th><th>سیگنال جانشین</th><th>ظرفیت فرضی تومان</th><th>امکان اجرای صف</th></tr>{cells}</table></section>
    <section><h2>آزمون زمانی ۲۰۲۶</h2><p>بازده و افت به صورت اعشاری؛ 0.10 یعنی ۱۰٪. قیمت FIRST روز بعد صرفاً جانشین اجرا است. این جدول عملکرد قابل معامله تأییدشده نیست.</p><div dir="ltr">{result}</div></section>
    <section><h2>تصمیم فعلی</h2><p>ورود واقعی مسدود است تا کیفیت تعدیلات، تعرفه تاریخی، محدودیت قیمت و اجرای سفارش احراز شود. رابطه معکوس طلا و سهام نیز دائمی فرض نشده است.</p></section></main></html>'''
    (out/'dashboard.html').write_text(s)

if __name__=='__main__': main()
