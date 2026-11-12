"""Fail closed on missing evidence; research scores cannot become live orders."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone

REQUIRED=['currency_verified','historical_adjustment_verified','historical_rules_verified','order_book_verified',
          'fee_schedule_verified','instrument_status_verified','calendars_verified','model_promotion_approved','human_order_confirmation']

def live_gate(evidence):
    missing=[k for k in REQUIRED if evidence.get(k) is not True]
    return {'allowed':not missing,'missing':missing,'state':'REVIEWABLE_PLAN' if not missing else 'BLOCKED'}

def archive_jsonl(source_file,destination):
    """Import timestamped observations without inventing missing fields or identity."""
    source_file=Path(source_file);destination=Path(destination)
    if destination.exists():raise FileExistsError('Archive is append-only: use a new destination')
    records=[];last={}
    for n,line in enumerate(source_file.read_text().splitlines(),1):
        r=json.loads(line)
        required=['instrument_id','observed_at','exchange_timestamp','source','kind','payload']
        if any(k not in r for k in required):raise ValueError(f'Incomplete observation line {n}')
        for key in ['observed_at','exchange_timestamp']:
            t=datetime.fromisoformat(r[key].replace('Z','+00:00'))
            if t.tzinfo is None:raise ValueError('Explicit timezone required')
        observed=datetime.fromisoformat(r['observed_at'].replace('Z','+00:00'))
        exchange=datetime.fromisoformat(r['exchange_timestamp'].replace('Z','+00:00'))
        if exchange>observed:raise ValueError('Exchange time later than observation')
        key=(r['instrument_id'],r['kind'])
        if key in last and exchange<last[key]:raise ValueError('Out-of-order exchange timestamps')
        last[key]=exchange
        if r['kind']=='book':
            p=r['payload']
            if not all(k in p for k in ['bids','asks','lower_limit','upper_limit','status']):raise ValueError('Incomplete book/limits/status')
            if p['lower_limit']>p['upper_limit']:raise ValueError('Inverted limits')
            for level in p['bids']+p['asks']:
                if level['price']<=0 or level['quantity']<0:raise ValueError('Invalid book level')
        # Snapshots do not establish own queue position or cancellations ahead.
        r['queue_position_verified']=False
        records.append(r)
    raw=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records).encode()
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
    return {'records':len(records),'sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':hashlib.sha256(source_file.read_bytes()).hexdigest()}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--archive',required=True);a=p.parse_args()
    print(json.dumps(archive_jsonl(a.input,a.archive),indent=2))
