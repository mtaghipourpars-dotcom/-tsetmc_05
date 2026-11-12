import argparse,json
from pathlib import Path
from engine import ROOT,run
from behavior import analyze

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT.parent/'Data');a=p.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text());out=ROOT/'results'
    frames,days,panel,values,share,returns,result=run(a.data,out,cfg)
    analyze(a.data,out,frames,days,panel,values,share,returns,result)
