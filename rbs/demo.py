"""Scripted, truth-aware plumbing demonstration. Never an LLM evaluation."""
from __future__ import annotations
from pathlib import Path
import hashlib
from .io import file_hash, read_json
from .packets import MODE_DEMO, load_manifest, prepare
from .report import write_report
from .store import import_adjudication, import_submission


def _number(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)

def run_demo(config: dict, out: Path, packets: Path) -> dict:
    prepared = prepare(config, out, packets, mode=MODE_DEMO)
    manifest = load_manifest(out)
    for job in manifest['jobs']:
        # The simulator reads the answer key intentionally: testing the harness,
        # including shared misses and wrong-target blocks, is its ONLY purpose.
        key = f"{job['case_id']}/{job['repeat']}"
        common = _number(key) % 4 == 0
        detect = not common and _number(key + '/' + job['slot']) % 3 != 0
        if job['arm_id'] == 'panel_informed':
            detect = detect and _number(key + '/note') % 5 != 0
        if job['arm_id'] == 'solo_budget':
            detect = not common
        fault = job['variant'] == 'faulty'
        wrong_block = _number(key + '/wrong/' + job['slot']) % 7 == 0
        block = (fault and detect) or wrong_block
        meta = read_json(out / 'frozen/fixtures' / job['case_id'] / 'metadata.json')
        findings = []
        if block:
            findings.append({'finding_id':'f1','file':'candidate.py','line_start':1,
                             'line_end':job['candidate_lines'],'severity':'medium',
                             'description':meta['target_defect'] if fault and detect else 'SCRIPTED wrong-target finding for pipeline testing.',
                             'evidence':'SYNTHETIC_DEMO: generated from the answer key; not a model observation.'})
        submission = {'schema_version':1,'job_id':job['job_id'],'packet_sha256':job['packet_sha256'],
                      'execution':{'status':'ok','model_id':'mock-truth-aware-simulator','harness_id':'rbs-scripted-demo-0.1',
                                   'input_tokens':0,'output_tokens':0,'cost_usd':0,'latency_seconds':0,
                                   'isolation_attested':False,'trace_reference':'rbs/demo.py (scripted source, not an LLM trace)'},
                      'review':{'verdict':'request_changes' if block else 'approve','findings':findings,
                                'summary':'SCRIPTED SYNTHETIC DEMONSTRATION ONLY. No model was called.'}}
        path = import_submission(out, submission)
        if block:
            state = 'not_applicable' if not fault else 'detected' if detect else 'missed'
            import_adjudication(out, {'schema_version':1,'job_id':job['job_id'],'submission_sha256':file_hash(path),
                                     'target_detection':state,'finding_ids':['f1'] if state == 'detected' else [],
                                     'rationale':'SCRIPTED annotation from simulator truth state; not independent adjudication.',
                                     'grader_id':'mock-truth-aware-grader','method':'mock_demo',
                                     'evidence_reference':'frozen fixture test_oracle.py; demonstration only'})
    return {**prepared, **write_report(out, out / 'report')}
