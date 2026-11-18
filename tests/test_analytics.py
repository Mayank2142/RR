import json
from pathlib import Path
import unittest
import numpy as np
from backend.analytics.context import load_context, classify, add_baselines, CREDITED
from backend.analytics.scoring import score_players, ecdf, WEIGHTS

ROOT=Path(__file__).resolve().parents[1]

class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw,cls.audit=load_context()
        cls.labelled=classify(cls.raw)
        cls.d=add_baselines(cls.labelled)
        cls.snapshot=json.loads((ROOT/'output'/'analysis.json').read_text(encoding='utf-8'))

    def test_extra_field_is_not_a_run_quantity(self):
        d=self.raw
        self.assertEqual(set(d.loc[d.extras_type.isna(),'extras1_runs']),{6})
        self.assertEqual(set(d.loc[d.extras_type.eq('wide'),'extras1_runs']),{2})
        self.assertEqual(int(self.d.runs.sum()),sum(p['metrics']['runs'] for p in self.snapshot['rankings']['bat'])+
                         int(self.d[~self.d.striker_id.isin([p['id'] for p in self.snapshot['rankings']['bat']])].runs.sum()))

    def test_context_is_pre_delivery(self):
        for _,g in self.raw.groupby(['match_id','innings']):
            np.testing.assert_array_equal(g.wickets_before.to_numpy(),np.r_[0,np.cumsum(g.is_wicket.to_numpy(dtype=int))[:-1]])
        self.assertTrue((self.raw.groupby(['match_id','innings']).head(1).striker_runs_before==0).all())
        self.assertTrue((self.raw.groupby(['match_id','innings','partnership_id']).head(1).partnership_runs_before==0).all())

    def test_pressure_does_not_use_outcome_or_current_ball(self):
        altered=self.raw.copy()
        altered['win_team_id']=-1;altered['result']='UNKNOWN';altered['runs']=6;altered['is_wicket']=True
        x=classify(altered)
        for k in ['bat_pressure','bowl_pressure']:
            np.testing.assert_array_equal(x[k].to_numpy(),self.labelled[k].to_numpy())

    def test_model_subset_is_valid(self):
        self.assertFalse(self.d.extras_type.isin(['wide','Overstep','other','Penalty']).any())
        self.assertTrue(self.d.innings.isin([1,2]).all())
        self.assertFalse(self.d.revised.any())
        self.assertFalse(self.d.ambiguous_innings.any())
        self.assertFalse(self.d.sequence_bad.any())
        self.assertEqual(len(self.d),self.snapshot['overview']['legal_model_deliveries'])
        self.assertEqual(self.d.source_row.nunique(),len(self.d))

    def test_bowling_wickets_exclude_runouts(self):
        self.assertFalse(self.d.loc[self.d.bowl_out.eq(1),'dismissal_type'].isin(['RunOut','Retire Out']).any())
        self.assertEqual(int(self.d.bowl_out.sum()),int(self.d.dismissal_type.isin(CREDITED).sum()))

    def test_scores_and_exports_reproduce(self):
        for kind in ['bat','bowl']:
            ranked,_,_=score_players(self.d,kind)
            stored=self.snapshot['rankings'][kind]
            self.assertEqual(ranked.index.tolist(),[p['id'] for p in stored])
            np.testing.assert_allclose(ranked.score,[p['score'] for p in stored],atol=.00006)
            self.assertEqual(len(set(p['id'] for p in stored)),len(stored))
            for p in stored:
                expected=sum(p['components'][k]*v for k,v in WEIGHTS.items())
                self.assertAlmostEqual(p['score'],expected,places=3)
                self.assertGreaterEqual(p['score_low'],0);self.assertLessEqual(p['score_high'],100)
                self.assertLess(p['score_low'],p['score_high'])
                self.assertIsNone(p['components']['match_impact'])

    def test_ties_are_equal_and_lower_bowling_runs_benefit(self):
        self.assertEqual(ecdf([2,2],[1,2,2,3]).tolist(),[50,50])
        self.assertGreater(float(ecdf([.3],[-.3,0,.3])[0]),float(ecdf([-.3],[-.3,0,.3])[0]))

    def test_reports_use_same_snapshot(self):
        frontend=json.loads((ROOT/'frontend'/'public'/'analysis.json').read_text(encoding='utf-8'))
        for kind in ['bat','bowl']:
            self.assertEqual(frontend['rankings'][kind],self.snapshot['rankings'][kind])
        self.assertTrue((ROOT/'output'/'pdf'/'SupeRR_Selector_Report.pdf').exists())

if __name__=='__main__':unittest.main(verbosity=2)
