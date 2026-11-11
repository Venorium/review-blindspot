from pathlib import Path
import tempfile
import unittest
from rbs.io import RBSError, digest, read_json, write_json
from rbs.schema import validate_submission, validate_adjudication
JOB={'job_id':'job-test','packet_sha256':'a'*64,'candidate_lines':3,'variant':'faulty'}
def submission(verdict='approve'):
    return {'schema_version':1,'job_id':JOB['job_id'],'packet_sha256':JOB['packet_sha256'],
            'execution':{'status':'ok','model_id':'test-model','harness_id':'unit-test','input_tokens':None,'output_tokens':None,'cost_usd':None,'latency_seconds':None,'isolation_attested':True,'trace_reference':None},
            'review':{'verdict':verdict,'summary':'Review summary.','findings':[]}}
def blocking():
    obj=submission('request_changes')
    obj['review']['findings']=[{'finding_id':'f1','file':'candidate.py','line_start':1,'line_end':2,'severity':'medium','description':'Contract violation.','evidence':'Concrete trigger and expected behavior.'}]
    return obj
class IOTests(unittest.TestCase):
    def test_hash_key_order(self): self.assertEqual(digest({'a':1,'b':2}),digest({'b':2,'a':1}))
    def test_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(RBSError):read_json(p)
    def test_nan(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(RBSError):read_json(p)
    def test_exclusive_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';write_json(p,{})
            with self.assertRaises(FileExistsError):write_json(p,{})
    def test_oversized_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_bytes(b' '*2_000_001)
            with self.assertRaises(RBSError):read_json(p)
class SubmissionTests(unittest.TestCase):
    def test_approve(self):validate_submission(submission(),JOB)
    def test_block(self):validate_submission(blocking(),JOB)
    def test_abstain(self):validate_submission(submission('abstain'),JOB)
    def test_missing_usage(self):
        obj=submission();validate_submission(obj,JOB);self.assertIsNone(obj['execution']['cost_usd'])
    def test_unknown_field(self):
        obj=submission();obj['extra']=1
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_wrong_job(self):
        obj=submission();obj['job_id']='../evil'
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_wrong_packet(self):
        obj=submission();obj['packet_sha256']='b'*64
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_block_needs_finding(self):
        with self.assertRaises(RBSError):validate_submission(submission('request_changes'),JOB)
    def test_approval_with_finding(self):
        obj=blocking();obj['review']['verdict']='approve'
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_lines(self):
        obj=blocking();obj['review']['findings'][0]['line_end']=4
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_path(self):
        obj=blocking();obj['review']['findings'][0]['file']='../../oracle.py'
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_bool_token_count(self):
        obj=submission();obj['execution']['input_tokens']=True
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_negative_cost(self):
        obj=submission();obj['execution']['cost_usd']=-1
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_inf_cost(self):
        obj=submission();obj['execution']['cost_usd']=float('inf')
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_error_not_approval(self):
        obj=submission();obj['execution']['status']='timeout'
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_error_null(self):
        obj=submission();obj['execution']['status']='provider_error';obj['review']=None;validate_submission(obj,JOB)
    def test_duplicate_finding(self):
        obj=blocking();obj['review']['findings']*=2
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
    def test_bool_version(self):
        obj=submission();obj['schema_version']=True
        with self.assertRaises(RBSError):validate_submission(obj,JOB)
class AdjudicationTests(unittest.TestCase):
    def annotation(self):return {'schema_version':1,'job_id':JOB['job_id'],'submission_sha256':'h','target_detection':'detected','finding_ids':['f1'],'rationale':'Same-defect trigger.','grader_id':'grader-a','method':'manual','evidence_reference':'witness'}
    def test_valid_detection(self):validate_adjudication(self.annotation(),JOB,blocking(),'h','EXTERNAL_REVIEWS_UNVERIFIED')
    def test_detection_needs_match(self):
        a=self.annotation();a['finding_ids']=[]
        with self.assertRaises(RBSError):validate_adjudication(a,JOB,blocking(),'h','EXTERNAL_REVIEWS_UNVERIFIED')
    def test_no_mock_in_real_run(self):
        a=self.annotation();a['method']='mock_demo'
        with self.assertRaises(RBSError):validate_adjudication(a,JOB,blocking(),'h','EXTERNAL_REVIEWS_UNVERIFIED')
    def test_wrong_submission(self):
        with self.assertRaises(RBSError):validate_adjudication(self.annotation(),JOB,blocking(),'other','EXTERNAL_REVIEWS_UNVERIFIED')
    def test_clean_not_target(self):
        with self.assertRaises(RBSError):validate_adjudication(self.annotation(),{**JOB,'variant':'correct'},blocking(),'h','EXTERNAL_REVIEWS_UNVERIFIED')
