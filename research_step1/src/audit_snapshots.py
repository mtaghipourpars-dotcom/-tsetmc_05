from pathlib import Path
import pandas as pd

MAPPING={'عيار':'Ayar','كهربا':'Kahroba','آلتون':'Alton','اهرم':'CharismaAhromi.ETF','موج':'Moj.ETF-LR','شتاب':'Shetab.ETF','توان':'Tavan.ETF-LR','اعتماد':'Etemad.Parsian.ETF'}
DATES={9:'2026-10-31',10:'2026-11-01',11:'2026-11-02',12:'2026-11-03',13:'2026-11-04',16:'2026-11-07',17:'2026-11-08',18:'2026-11-09',19:'2026-11-10',20:'2026-11-11'}
FIELDS={3:'VOL',4:'VALUE',5:'OPEN',6:'FIRST',7:'LAST',10:'CLOSE',13:'LOW',14:'HIGH'}

def audit_snapshots(data,frames,out):
    result=[]
    for p in sorted(data.glob('MarketWatch*.md')):
        day=int(p.stem.rsplit('_',1)[1]);date=pd.Timestamp(DATES[day])
        for line in p.read_text().splitlines():
            if not line.startswith('|'):continue
            row=[v.strip() for v in line.split('|')[1:-1]]
            if not row or row[0] not in MAPPING:continue
            sym=MAPPING[row[0]]
            for ix,col in FIELDS.items():
                a=float(row[ix].replace(',',''));b=float(frames[sym].loc[date,col])
                result.append(dict(date=str(date.date()),symbol=sym,column=col,snapshot=a,history=b,
                     matches=abs(a-b)<=max(.01,abs(b)*1e-5),ratio=a/b if b else None))
    df=pd.DataFrame(result);df.to_csv(out/'snapshot_history_crosscheck.csv',index=False)
    return dict(comparisons=len(df),mismatches=int((~df.matches).sum()))
