import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from engine import *
from governance import live_gate,archive_jsonl

class AdaptiveTests(unittest.TestCase):
    def cfg(self):return json.loads((ROOT/'config.json').read_text())
    def fixture(self):
        days=pd.bdate_range('2024-01-01',periods=70)
        d=pd.DataFrame(dict(FIRST=100.,HIGH=101.,LOW=99.,CLOSE=100.,LAST=100.,VALUE=1e12,VOL=1e10,OPENINT=100,valid=True,single=False,corporate_unknown=False),index=days)
        row=dict(i=20,date=str(days[20].date()),symbol='Ayar',group='gold',regime='gold_lead',gap=False,corporate_unknown=False,single=False,capacity=1e9,
              r3=-.02,relative_activity=1.,last_first=.01,location=.7,overhang_change=-.2,group_share_change=.1,stress=0.,repair=True,relay=False,supply_relief=False,simple=True,momentum=False)
        return {'Ayar':d},days,pd.DataFrame([row]),row
    def test_future_reward_rejected(self):
        m=Learner(self.cfg())
        with self.assertRaises(AssertionError):m.add_matured([{'maturity_i':12}],11)
    def test_partial_exit_cash_ledger(self):
        f,d,p,_=self.fixture();f['Ayar'].loc[d[26]:,['FIRST','CLOSE','LAST']]=200
        f['Ayar'].loc[d[26],'VALUE']=980000
        curve,tr,orders,_,_,_=simulate(f,d,p,[],self.cfg(),'repair',10000,fee=.01,slip=0)
        self.assertTrue((orders.status=='PARTIAL').any());self.assertAlmostEqual(curve.equity.iloc[-1],19603)
        self.assertEqual(tr.iloc[0]['delay_sessions'],1)
        self.assertGreater(curve.loc[26,'unsettled_cash'],0)
        self.assertEqual(curve.loc[26,'free_cash'],1)
    def test_allocation_not_scaled_down(self):
        f,d,p,_=self.fixture();p['capacity']=1
        curve,tr,orders,*_=simulate(f,d,p,[],self.cfg(),'repair',10000)
        self.assertFalse(len(tr));self.assertEqual(curve.equity.iloc[-1],10000)
    def test_queue_shock_not_stop_guarantee(self):
        f,d,p,_=self.fixture();f['Ayar'].loc[d[26:31],'single']=True
        f['Ayar'].loc[d[31]:,['FIRST','CLOSE','LAST']]=85
        curve,tr,*_=simulate(f,d,p,[],self.cfg(),'repair',10000,fee=0,slip=0)
        self.assertEqual(tr.iloc[0]['delay_sessions'],5);self.assertAlmostEqual(tr.iloc[0]['net_return'],-.15)
    def test_live_gate_blocks_research(self):
        gate=live_gate(self.cfg());self.assertFalse(gate['allowed']);self.assertIn('human_order_confirmation',gate['missing'])
    def test_rule_quarantine(self):
        f,d,p,row=self.fixture();d=pd.bdate_range('2026-10-15',periods=70)
        row.update(i=20,date=str(d[20].date()),group='equity')
        change=np.flatnonzero(d>=pd.Timestamp('2026-11-07'))[0];row['i']=int(change)+1
        ok,reason=safety(row,d,self.cfg());self.assertFalse(ok);self.assertEqual(reason,'reported_rule_change_quarantine')
    def test_features_past_invariant(self):
        f,d,_,_=self.fixture();base=f['Ayar']
        frames={s:base.copy() for s in GOLD+EQUITY+[DEFENSIVE]}
        before=build_features(frames,d,self.cfg())[0]
        for df in frames.values():df.loc[d[66]:,['FIRST','LAST','CLOSE']]*=2
        after=build_features(frames,d,self.cfg())[0]
        pd.testing.assert_frame_equal(before[before.i<66].reset_index(drop=True),after[after.i<66].reset_index(drop=True))
    def test_archive_timezone_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src.jsonl';src.write_text(json.dumps(dict(instrument_id='x',observed_at='2026-01-01T10:00:00',exchange_timestamp='2026-01-01T09:59:00',source='synthetic_test',kind='trade',payload={})))
            with self.assertRaises(ValueError):archive_jsonl(src,Path(tmp)/'out.jsonl')

if __name__=='__main__':unittest.main()
