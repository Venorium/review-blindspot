from pathlib import Path
import tempfile
import unittest
from rbs.io import ROOT,RBSError,read_json,write_json
from rbs.packets import prepare,load_manifest
from rbs.exchange import wrap_review
from rbs.store import import_submission

class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        c=read_json(ROOT/'configs/smoke.json');c['case_ids']=['c01'];c['arms']=c['arms'][:1]
        self.run=self.root/'run';self.packets=self.root/'packets';prepare(c,self.run,self.packets)
        self.job=load_manifest(self.run)['jobs'][0];self.packet=self.packets/self.job['job_id']
        self.review=self.root/'review.json';self.execution=self.root/'execution.json';self.out=self.root/'submission.json'
        self.ex={'status':'ok','model_id':'unit-model','harness_id':'test-transport','input_tokens':None,'output_tokens':None,'cost_usd':None,'latency_seconds':None,'isolation_attested':False,'trace_reference':None}
    def test_wrap_and_import(self):
        write_json(self.review,{'verdict':'approve','findings':[],'summary':'Unit transport test.'});write_json(self.execution,self.ex)
        wrap_review(self.packet,self.review,self.execution,self.out);import_submission(self.run,read_json(self.out))
    def test_error_wrap(self):
        write_json(self.review,None);write_json(self.execution,{**self.ex,'status':'timeout'})
        wrap_review(self.packet,self.review,self.execution,self.out);self.assertIsNone(read_json(self.out)['review'])
    def test_placeholder_model_rejected(self):
        write_json(self.review,{'verdict':'approve','findings':[],'summary':'Test.'});write_json(self.execution,{**self.ex,'model_id':'REPLACE_WITH_MODEL'})
        with self.assertRaises(RBSError):wrap_review(self.packet,self.review,self.execution,self.out)
    def test_packet_tamper(self):
        (self.packet/'SPEC.md').write_text('tampered')
        with self.assertRaises(RBSError):wrap_review(self.packet,self.review,self.execution,self.out)
