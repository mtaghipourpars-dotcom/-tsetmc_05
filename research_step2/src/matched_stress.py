"""Stress the exact base adaptive trades without refitting or changing quantities."""
import json,argparse
from pathlib import Path
import pandas as pd
from engine import ROOT,load

def run(data,out):
    frames,days=load(data,out);tr=pd.read_csv(out/'adaptive_trades.csv');records=[]
    for t in tr.to_dict('records'):
        d=frames[t['symbol']];entry=pd.Timestamp(t['entry']);ei=days.get_loc(entry);qty=int(t['qty'])
        fee=.003;slip=.002;buy=float(d.loc[entry,'FIRST'])*(1+slip);cost=qty*buy*(1+fee)
        due=ei+int(t['h'])+3;left=qty;cash=0.;jlast=None
        for j in range(due,len(days)):
            r=d.loc[days[j]]
            if r.single:continue
            px=float(r.FIRST)*(1-slip);n=min(left,int(.003*float(r.VALUE)/px));cash+=n*px*(1-fee);left-=n
            if left==0:jlast=j;break
        records.append(dict(symbol=t['symbol'],entry=t['entry'],base_exit=t['exit'],base_net_return=t['net_return'],
            fixed_qty=qty,stress_net_return=cash/cost-1 if left==0 else None,
            stress_exit=str(days[jlast].date()) if jlast is not None else None,remaining=left,
            stress_entry_capacity_verified=False,notice='same_quantity_conditioned_on_entry_filled_not_portfolio_return'))
    pd.DataFrame(records).to_csv(out/'matched_trade_stress.csv',index=False)
    print(pd.DataFrame(records).to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args();run(a.data,ROOT/'results')
