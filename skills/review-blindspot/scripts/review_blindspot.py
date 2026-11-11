"""Local review evidence ledger. Python stdlib + Git; never executes project code."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

VERSION = '0.1.0'
MAX_FILES = 2000
MAX_BYTES = 256 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024


class ReviewError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ReviewError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    if path.is_symlink() or path.stat().st_size > MAX_JSON:
        raise ReviewError('JSON must be a regular file smaller than 2 MiB')
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda value: fail('Non-finite JSON number'))


def fail(message):
    raise ReviewError(message)


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write('\n')


def fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ReviewError(f'Expected fields: {names}')


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 10000:
        raise ReviewError(f'{label} must be a nonempty string, at most 10000 characters')
    return value


class Git:
    def __init__(self, repo):
        self.repo = Path(repo).resolve()
        # Ignore inherited repository/config overrides; never invoke a shell, pager,
        # external diff, text converter, fsmonitor hook, or configured content filter.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
        self.options = ['-c', 'core.fsmonitor=false', '--no-pager']
        filters = self.run('config', '--name-only', '--get-regexp',
                           r'^filter\..*\.(clean|smudge|process|required)$', allowed=(0, 1))
        for key in filters.decode('utf-8').splitlines():
            self.options.extend(['-c', key + ('=false' if key.endswith('.required') else '=')])

    def run(self, *args, allowed=(0,)):
        result = subprocess.run(['git', *self.options, '-C', str(self.repo), *args],
                                env=self.env, capture_output=True, timeout=30, shell=False)
        if result.returncode not in allowed:
            raise ReviewError(result.stderr.decode('utf-8', errors='replace').strip()
                              or 'Git command failed')
        return result.stdout

    def commit(self, ref):
        return self.run('rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()


def hash_file(path):
    if path.stat().st_size > MAX_BYTES:
        raise ReviewError(f'File exceeds the 256 MiB capture limit: {path.name}')
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            value.update(chunk)
    return value.hexdigest()


def snapshot(repo, base='HEAD'):
    git = Git(repo)
    root = Path(os.fsdecode(git.run('rev-parse', '--show-toplevel')).strip()).resolve()
    git.repo = root
    if git.run('ls-files', '--unmerged', '-z'):
        raise ReviewError('Resolve Git merge conflicts before capturing a review')
    base_id, head = git.commit(base), git.commit('HEAD')
    # Do not recurse into submodule repositories (which have their own executable
    # configuration). Keep every base/index gitlink as an explicit unsupported gap.
    gitlinks = set()
    for output in (git.run('ls-files', '--stage', '-z'), git.run('ls-tree', '-r', '-z', base_id)):
        for entry in output.split(b'\0'):
            if entry.startswith(b'160000 ') and b'\t' in entry:
                gitlinks.add(os.fsdecode(entry.split(b'\t', 1)[1]))
    names = git.run('diff', '--name-only', '-z', '--no-renames', '--no-ext-diff',
                    '--no-textconv', '--ignore-submodules=all', base_id, '--')
    names += git.run('ls-files', '--others', '--exclude-standard', '-z')
    paths = sorted(set(os.fsdecode(name) for name in names.split(b'\0') if name) | gitlinks)
    if len(paths) > MAX_FILES:
        raise ReviewError(f'Review exceeds {MAX_FILES} changed paths; narrow the change first')
    records, size = [], 0
    for name in paths:
        path = root / name
        if not path.parent.resolve().is_relative_to(root):
            raise ReviewError(f'Changed path leaves the repository through a link: {name}')
        if name in gitlinks:
            record = {'path': name, 'kind': 'unsupported', 'sha256': None, 'executable': False}
        elif path.is_symlink():
            record = {'path': name, 'kind': 'symlink', 'sha256': digest(os.readlink(path)), 'executable': False}
        elif not path.exists():
            record = {'path': name, 'kind': 'deleted', 'sha256': None, 'executable': False}
        elif path.is_file():
            size += path.stat().st_size
            if size > MAX_BYTES:
                raise ReviewError('Changed files exceed the 256 MiB capture limit')
            record = {'path': name, 'kind': 'file', 'sha256': hash_file(path),
                      'executable': bool(path.stat().st_mode & stat.S_IXUSR)}
        else:
            record = {'path': name, 'kind': 'unsupported', 'sha256': None, 'executable': False}
        records.append(record)
    return {'schema_version': 1, 'tool_version': VERSION, 'repo': str(root),
            'base_ref': base, 'base_commit': base_id, 'head_commit': head, 'files': records}


def capture(repo, out=None, base='HEAD'):
    first = snapshot(repo, base)
    if first != snapshot(repo, base):
        raise ReviewError('Repository changed during capture; retry when edits have stopped')
    root = Path(first['repo'])
    if out is None:
        if Path(tempfile.gettempdir()).resolve().is_relative_to(root):
            raise ReviewError('Temporary directory is inside the repository; use --out outside it')
        out = Path(tempfile.mkdtemp(prefix='review-blindspot-'))
    else:
        out = Path(out).resolve()
        if out.is_relative_to(root):
            raise ReviewError('Choose a new review directory outside the repository')
        out.mkdir(parents=True, exist_ok=False)
    if out.resolve().is_relative_to(root):
        raise ReviewError('Temporary directory is inside the repository; use --out outside it')
    write_json(out / 'snapshot.json', first)
    write_json(out / 'review.json', {'schema_version': 1, 'snapshot_id': digest(first),
        'reviewer_context': 'unspecified',
        'files': [{'path': f['path'], 'disposition': 'unreviewed', 'reason': ''} for f in first['files']],
        'checks': []})
    return {'state': 'captured', 'review': str(out.resolve()), 'changed_files': len(first['files']),
            'snapshot_id': digest(first), 'next': 'Inspect the change; fill review.json; run check.'}


def validate_ledger(review, frozen, directory):
    fields(review, 'schema_version snapshot_id reviewer_context files checks')
    if type(review['schema_version']) is not int or review['schema_version'] != 1:
        raise ReviewError('Unsupported review schema_version')
    if review['snapshot_id'] != digest(frozen):
        raise ReviewError('Review is not bound to this snapshot')
    if review['reviewer_context'] not in ('unspecified', 'same_session', 'fresh_session'):
        raise ReviewError('Invalid reviewer_context')
    expected = {f['path'] for f in frozen['files']}
    if not isinstance(review['files'], list) or not isinstance(review['checks'], list):
        raise ReviewError('files and checks must be lists')
    seen = set()
    for item in review['files']:
        fields(item, 'path disposition reason')
        name = text(item['path'], 'path')
        if name not in expected or name in seen:
            raise ReviewError('Every captured path must appear exactly once')
        seen.add(name)
        if item['disposition'] not in ('unreviewed', 'reviewed', 'excluded'):
            raise ReviewError('Invalid file disposition')
        if not isinstance(item['reason'], str):
            raise ReviewError('File reason must be a string')
        if item['disposition'] != 'unreviewed':
            text(item['reason'], 'File review scope or exclusion reason')
    if seen != expected:
        raise ReviewError('Every captured path must appear exactly once')
    ids = set()
    for item in review['checks']:
        fields(item, 'id claim files status evidence')
        identity = text(item['id'], 'check id')
        if identity in ids:
            raise ReviewError('Duplicate check id')
        ids.add(identity)
        text(item['claim'], 'claim')
        if (not isinstance(item['files'], list) or not item['files']
                or any(not isinstance(p, str) or p not in expected for p in item['files'])):
            raise ReviewError('Each check must reference captured paths')
        if item['status'] not in ('unverified', 'supported', 'contradicted', 'inconclusive'):
            raise ReviewError('Invalid check status')
        if not isinstance(item['evidence'], list):
            raise ReviewError('Evidence must be a list')
        for proof in item['evidence']:
            fields(proof, 'kind reference observation sha256')
            text(proof['reference'], 'evidence reference')
            text(proof['observation'], 'evidence observation')
            if proof['kind'] == 'inspection':
                if proof['sha256'] is not None:
                    raise ReviewError('Inspection evidence uses the code snapshot; sha256 must be null')
            elif proof['kind'] == 'test':
                ref = Path(proof['reference'])
                artifact = directory / ref
                if ref.is_absolute() or not artifact.resolve().is_relative_to(directory.resolve()):
                    raise ReviewError('Test evidence must stay inside the review directory')
                if artifact.is_symlink() or not artifact.is_file() or hash_file(artifact) != proof['sha256']:
                    raise ReviewError('Test evidence is missing or changed: ' + proof['reference'])
            else:
                raise ReviewError('Evidence kind must be inspection or test')


def check(directory):
    directory = Path(directory).resolve()
    frozen = read_json(directory / 'snapshot.json')
    fields(frozen, 'schema_version tool_version repo base_ref base_commit head_commit files')
    if frozen['schema_version'] != 1 or frozen['tool_version'] != VERSION:
        raise ReviewError('Unsupported snapshot version')
    if not isinstance(frozen['files'], list):
        raise ReviewError('Snapshot files must be a list')
    for item in frozen['files']:
        fields(item, 'path kind sha256 executable')
    review = read_json(directory / 'review.json')
    validate_ledger(review, frozen, directory)
    live = snapshot(frozen['repo'], frozen['base_ref'])
    stale = live != frozen
    issues = []
    if review['reviewer_context'] == 'unspecified':
        issues.append('Reviewer context is unspecified')
    for item in review['files']:
        if item['disposition'] != 'reviewed':
            issues.append(item['path'] + ': ' + item['disposition'])
        elif not any(item['path'] in c['files'] for c in review['checks']):
            issues.append(item['path'] + ': no check records')
    for item in frozen['files']:
        if item['kind'] in ('symlink', 'unsupported'):
            issues.append(item['path'] + ': unsupported scope (' + item['kind'] + ')')
    for item in review['checks']:
        if item['status'] in ('unverified', 'inconclusive') or not item['evidence']:
            issues.append(item['id'] + ': unresolved or missing evidence')
    statuses = Counter(item['status'] for item in review['checks'])
    state = ('stale' if stale else 'no_changes' if not frozen['files'] else
             'attention_required' if statuses['contradicted'] else 'incomplete' if issues else 'documented')
    return {'schema_version': 1, 'state': state, 'snapshot_id': digest(frozen),
            'reviewer_context': review['reviewer_context'], 'changed_files': len(frozen['files']),
            'reviewed_files': sum(f['disposition'] == 'reviewed' for f in review['files']),
            'checks': dict(statuses), 'gaps': issues, 'records': review['checks'],
            'freshness': 'changed' if stale else 'matches_capture',
            'limitations': ['A documented review is not an approval or a correctness certificate.',
                'Evidence content and semantic coverage are declared by the reviewer, not verified by this tool.',
                'A fresh session is not proof of independence; same-session self-review is identified.',
                'Ignored files and unchanged dependencies are outside automatic capture.',
                'No project code, test, model, hook or content filter is executed by this helper.']}


def cell(value):
    value = html.escape(str(value), quote=False).replace('\n', ' ').replace('\r', ' ')
    value = ''.join(c if ord(c) >= 32 and ord(c) != 127 else f'\\u{ord(c):04x}' for c in value)
    for char in ('\\', '|', '`', '*', '_', '[', ']'):
        value = value.replace(char, '\\' + char)
    return value


def render(result):
    lines = ['# Review Blind Spot — Codex review', '', '**' + result['state'].upper() + '**', '',
        f"Files recorded as reviewed: {result['reviewed_files']}/{result['changed_files']} · "
        f"Freshness: {result['freshness']} · Context: {result['reviewer_context']}", '',
        '> Evidence tracking, not an approval or a bug-free guarantee.', '',
        '| Claim | Status | Evidence |', '| --- | --- | --- |']
    for record in result['records']:
        proof = '; '.join(p['kind'] + ': ' + p['reference'] + ' — ' + p['observation'] for p in record['evidence'])
        lines.append(f"| {cell(record['claim'])} | {record['status']} | {cell(proof) or 'missing'} |")
    lines += ['', '## Gaps', ''] + (['- ' + cell(x) for x in result['gaps']] or ['None recorded.'])
    if result['state'] == 'stale':
        lines += ['', '**Code or scope changed. Capture again and reassess; do not reuse this conclusion.**']
    lines += ['', '## Limits', ''] + ['- ' + item for item in result['limitations']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('capture', help='Capture Git change metadata; never copy source contents')
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--base', default='HEAD', help='Commit/ref compared with the current working tree')
    p.add_argument('--out', type=Path, help='New directory outside repo; default: system temp')
    p.add_argument('--json', action='store_true')
    p = subs.add_parser('check', help='Check coverage records, evidence hashes and code freshness')
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--out', type=Path, help='New directory for REPORT.md and summary.json')
    p.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'capture':
            result = capture(args.repo, args.out, args.base)
            if args.json:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            else:
                print(f"Captured {result['changed_files']} changed files.\nReview: {result['review']}\n{result['next']}")
            return 0
        result = check(args.review)
        if args.out:
            out = args.out.resolve()
            if out.is_relative_to(Path(read_json(args.review / 'snapshot.json')['repo'])):
                raise ReviewError('Report output must be outside the repository')
            out.mkdir(parents=True, exist_ok=False)
            write_json(out / 'summary.json', result)
            with (out / 'REPORT.md').open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(render(result))
        print(json.dumps(result, ensure_ascii=True, indent=2) if args.json else render(result))
        return 0 if result['state'] in ('documented', 'no_changes') else 1
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        error = {'state': 'invalid_artifacts', 'error': str(exc)}
        print(json.dumps(error, ensure_ascii=True) if args.json else 'ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
