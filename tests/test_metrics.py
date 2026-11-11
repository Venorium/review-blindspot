import unittest
from rbs.metrics import bootstrap_family_delta,outcome,summarize,target_state

def row(slot='r1',verdict='approve',variant='faulty',annotation=None,status='ok',case='c01',arm='panel_blind',repeat=0):
    sub=None if status=='missing' else {'execution':{'status':status,'input_tokens':None,'output_tokens':None,'cost_usd':None,'latency_seconds':None,'isolation_attested':False},'review':{'verdict':verdict,'findings':[]} if status=='ok' else None}
    return {'slot':slot,'arm_id':arm,'case_id':case,'family_id':case,'repeat':repeat,'variant':variant,'submission':sub,'annotation':{'target_detection':annotation} if annotation else None}
class MetricsTests(unittest.TestCase):
    def test_wrong_target_block(self):
        r=row(verdict='request_changes',annotation='missed');self.assertEqual(target_state(r),0);self.assertEqual(outcome([r])['gate'],'reject');self.assertEqual(outcome([r])['target'],'missed')
    def test_ungraded_block(self):self.assertIsNone(target_state(row(verdict='request_changes')))
    def test_missing_cannot_approve(self):self.assertEqual(outcome([row(),row(slot='r2',status='missing')])['gate'],'unresolved')
    def test_abstain_cannot_approve(self):self.assertEqual(outcome([row(verdict='abstain')])['gate'],'unresolved')
    def test_block_and_missing(self):
        g=outcome([row(verdict='request_changes'),row(slot='r2',status='missing')]);self.assertEqual(g['gate'],'reject');self.assertFalse(g['complete_decisive'])
    def test_common_miss(self):self.assertEqual(outcome([row(),row(slot='r2')])['target'],'missed')
    def test_one_target_detection(self):self.assertEqual(outcome([row(verdict='request_changes',annotation='detected'),row(slot='r2',status='timeout')])['target'],'detected')
    def test_bounds_with_missing(self):
        a=summarize([row(status='missing'),row(variant='correct',status='missing')],'X')['arms'][0]
        self.assertEqual(a['unsafe_approval_bounds_all_scheduled'],[0,1]);self.assertEqual(a['control_rejection_bounds_all_scheduled'],[0,1]);self.assertEqual(a['target_recall_bounds'],[0,1]);self.assertIsNone(a['usage']['cost_usd']['known_sum'])
    def test_zero_denominator(self):self.assertEqual(summarize([row(variant='correct')],'X')['arms'][0]['unsafe_approval_bounds_all_scheduled'],[None,None])
    def test_repeats_not_families(self):
        d=bootstrap_family_delta({'a':[1]*15});self.assertEqual(d['family_count'],1);self.assertIsNone(d['bootstrap_percentile_95'])
    def test_reproducible_bootstrap(self):
        a={'a':[1,0],'b':[-1,0],'c':[0]};self.assertEqual(bootstrap_family_delta(a),bootstrap_family_delta(a))
    def test_known_joint_misses(self):
        rows=[row(slot=s,case=c,verdict=v,annotation='detected' if v=='request_changes' else None) for c,v in [('a','approve'),('b','request_changes')] for s in ['r1','r2']]
        d=summarize(rows,'X')['pairwise_joint_misses'][0];self.assertEqual(d['joint_miss_rate'],.5);self.assertEqual(d['excess_joint_miss'],.25)
    def test_paired_difference(self):
        rows=[row(case=c,arm='panel_blind') for c in ['a','b']]+[row(case=c,arm='solo_budget',verdict='request_changes',annotation='detected') for c in ['a','b']]
        d=summarize(rows,'X')['paired_comparisons'][0];self.assertEqual(d['mean_delta'],1);self.assertEqual(d['family_count'],2)
    def test_demo_not_evidence(self):self.assertIs(summarize([row()],'SYNTHETIC_DEMO_NOT_MODEL_RESULTS')['results_are_model_evidence'],False)
