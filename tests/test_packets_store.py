from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from rbs.io import ROOT,RBSError,read_json
from rbs.packets import prepare,plan,load_manifest,check_packet,get_job
from rbs.store import import_submission,observations,export_grading_packets
from rbs.report import write_report
from rbs.demo import run_demo

def config():
    c=read_json(ROOT/'configs/smoke.json');c['case_ids']=['c01'];return c

def submission(job):return {'schema_version':1,'job_id':job['job_id'],'packet_sha256':job['packet_sha256'],'execution':{'status':'ok','model_id':'test-model','harness_id':'unit-test','input_tokens':None,'output_tokens':None,'cost_usd':None,'latency_seconds':None,'isolation_attested':True,'trace_reference':None},'review':{'verdict':'approve','findings':[],'summary':'Test review.'}}
class PacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);self.run=root/'run';self.packets=root/'packets';prepare(config(),self.run,self.packets);self.manifest=load_manifest(self.run);self.job=self.manifest['jobs'][0]
    def test_plan_count(self):self.assertEqual(plan(config())['review_jobs'],8)
    def test_no_answer_key(self):
        allowed={'before.py','candidate.py','SPEC.md','patch.diff','test_public.py','review_prompt.txt','review.schema.json','job.json'}
        for job in self.manifest['jobs']:
            folder=self.packets/job['job_id'];self.assertEqual({p.name for p in folder.iterdir()},allowed)
            p=read_json(folder/'job.json');self.assertNotIn('case_id',p);self.assertNotIn('variant',p);self.assertNotIn('arm_id',p)
    def test_valid_integrity(self):check_packet(self.manifest,self.job)
    def test_packet_tamper(self):
        (self.packets/self.job['job_id']/'candidate.py').write_text('# tampered')
        with self.assertRaises(RBSError):check_packet(self.manifest,self.job)
    def test_extra_file(self):
        (self.packets/self.job['job_id']/'answer.json').write_text('{}')
        with self.assertRaises(RBSError):check_packet(self.manifest,self.job)
    def test_unknown_job(self):
        with self.assertRaises(RBSError):get_job(self.manifest,'../../secret')
    def test_no_directory_reuse(self):
        with self.assertRaises(RBSError):prepare(config(),self.run,self.packets)
    def test_no_nested_packets(self):
        with self.assertRaises(RBSError):prepare(config(),self.run/'new',self.run/'new'/'public')
    def test_no_packets_in_repo(self):
        with self.assertRaises(RBSError):prepare(config(),self.run/'new',ROOT/'never-created-test-packets')
    def test_manifest_tamper(self):
        with (self.run/'manifest.json').open('a') as f:f.write(' ')
        with self.assertRaises(RBSError):load_manifest(self.run)
    def test_frozen_tamper(self):
        (self.run/'frozen/fixtures/c01/correct.py').write_text('pass')
        with self.assertRaises(RBSError):load_manifest(self.run)
    def test_import(self):
        import_submission(self.run,submission(self.job));_,rows=observations(self.run);self.assertEqual(sum(r['submission'] is not None for r in rows),1)
    def test_no_overwrite(self):
        obj=submission(self.job);import_submission(self.run,obj)
        with self.assertRaises(RBSError):import_submission(self.run,obj)
    def test_result_tamper(self):
        path=import_submission(self.run,submission(self.job))
        with path.open('a') as f:f.write(' ')
        with self.assertRaises(RBSError):observations(self.run)
    def test_deleted_result(self):
        path=import_submission(self.run,submission(self.job));path.unlink()
        with self.assertRaises(RBSError):observations(self.run)
    def test_mock_forbidden_external(self):
        obj=submission(self.job);obj['execution']['model_id']='mock-script'
        with self.assertRaises(RBSError):import_submission(self.run,obj)
    def test_incomplete_report(self):
        out=Path(self.tmp.name)/'report';write_report(self.run,out);self.assertEqual(read_json(out/'metrics.json')['arms'][0]['unsafe_approval_bounds_all_scheduled'],[0,1])
    def test_report_no_overwrite(self):
        out=Path(self.tmp.name)/'report';write_report(self.run,out)
        with self.assertRaises(RBSError):write_report(self.run,out)
    def test_no_grading_approval(self):
        import_submission(self.run,submission(self.job));self.assertEqual(export_grading_packets(self.run,Path(self.tmp.name)/'grading')['grading_packets'],0)
    def test_duplicate_arms(self):
        c=config();c['arms'].append(deepcopy(c['arms'][0]))
        with self.assertRaises(RBSError):plan(c)
    def test_unknown_case(self):
        c=config();c['case_ids']=['nonexistent']
        with self.assertRaises(RBSError):plan(c)
    def test_unsupported_track(self):
        c=config();c['track']='tool_enabled'
        with self.assertRaises(RBSError):plan(c)
class DemoTests(unittest.TestCase):
    def test_end_to_end_demo(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);result=run_demo(config(),root/'run',root/'packets');self.assertEqual(result['mode'],'SYNTHETIC_DEMO_NOT_MODEL_RESULTS');m=read_json(root/'run/report/metrics.json');self.assertFalse(m['results_are_model_evidence']);self.assertTrue(all(a['execution_status_counts']=={'ok':a['review_jobs']} for a in m['arms']))
