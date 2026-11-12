import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run import *

class EngineTests(unittest.TestCase):
    def fixture(self):
        days=pd.bdate_range('2024-01-01',periods=70)
        d=pd.DataFrame(dict(FIRST=100.,HIGH=101.,LOW=99.,CLOSE=100.,LAST=100.,VALUE=1e12,VOL=1e10,valid=True,single=False,corporate_unknown=False),index=days)
        scores=pd.DataFrame({'Ayar':np.nan},index=days);scores.iloc[20,0]=1
        corr=pd.Series(-.5,index=days)
        return {'Ayar':d},days,scores,corr
    def test_hand_cash_and_two_sided_fees(self):
        f,d,s,c=self.fixture();f['Ayar'].loc[d[26],['FIRST','CLOSE']]=200
        m,eq,tr,ev,_=simulate(f,d,s,c,10000,fee=.01,slip=0)
        self.assertEqual(tr.iloc[0]['qty'],99)
        self.assertAlmostEqual(eq.iloc[-1].equity,19603)
        self.assertAlmostEqual(m['fees_rial'],297)
        self.assertEqual(tr.iloc[0]['entry'],str(d[21].date()))
    def test_no_same_day_fill_and_no_capacity_fill(self):
        f,d,s,c=self.fixture();f['Ayar'].loc[d[21],'VALUE']=1
        m,_,tr,ev,_=simulate(f,d,s,c,10000)
        self.assertEqual(m['trades'],0);self.assertEqual(m['cancelled_entries'],1)
    def test_queue_delays_exit(self):
        f,d,s,c=self.fixture();f['Ayar'].loc[d[26:28],'single']=True
        m,_,tr,_,_=simulate(f,d,s,c,10000)
        self.assertEqual(tr.iloc[0]['exit_delay'],2)
    def test_open_position_not_free_cash(self):
        f,d,s,c=self.fixture();f['Ayar'].loc[d[26:],'single']=True
        m,eq,tr,_,_=simulate(f,d,s,c,10000)
        self.assertTrue(m['open_final']);self.assertLess(m['free_cash_final'],100)
        self.assertGreater(eq.iloc[-1].position_value,9000)
    def test_features_prefix_invariance(self):
        f,d,s,c=self.fixture();base=f['Ayar']
        frames={sym:base.copy() for sym in GOLD+EQUITY+[DEFENSIVE]}
        before=features(frames,d)[-1].iloc[:65].copy()
        for df in frames.values(): df.loc[d[65]:,['FIRST','LAST','CLOSE']]*=10
        after=features(frames,d)[-1].iloc[:65]
        pd.testing.assert_frame_equal(before,after)

if __name__=='__main__':unittest.main()
