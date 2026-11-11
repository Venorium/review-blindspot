"""Bind a provider's review object and operator-supplied metadata to one packet."""
from pathlib import Path
from .io import RBSError, digest, file_hash, read_json, write_json
from .schema import validate_submission


def wrap_review(packet: Path, review_path: Path, execution_path: Path, out: Path) -> dict:
    if packet.is_symlink() or not packet.is_dir():
        raise RBSError('Expected a real packet directory, not a symbolic link')
    job = read_json(packet / 'job.json')
    allowed = {'before.py','candidate.py','SPEC.md','patch.diff','test_public.py',
               'review_prompt.txt','review.schema.json'}
    artifact_names = set(job['artifacts'])
    if artifact_names not in (allowed, allowed | {'AUTHOR_NOTE.md'}):
        raise RBSError('Unexpected packet artifact paths')
    if any((packet / name).is_symlink() for name in artifact_names | {'job.json'}):
        raise RBSError('Symbolic links are forbidden in input packets')
    if set(p.name for p in packet.iterdir()) != set(job['artifacts']) | {'job.json'}:
        raise RBSError('Input packet changed or includes unauthorized files')
    artifacts = {name: file_hash(packet / name) for name in job['artifacts']}
    if artifacts != job['artifacts'] or digest(artifacts) != job['packet_sha256']:
        raise RBSError('Packet artifact hash mismatch')
    review = read_json(review_path)
    execution = read_json(execution_path)
    payload = {'schema_version':1,'job_id':job['job_id'],'packet_sha256':job['packet_sha256'],
               'execution':execution,'review':review}
    validate_submission(payload, {**job,'candidate_lines':len((packet/'candidate.py').read_text(encoding='utf-8').splitlines())})
    write_json(out,payload)
    return {'submission':str(out.resolve()),'job_id':job['job_id'],'network_calls_made':0}
