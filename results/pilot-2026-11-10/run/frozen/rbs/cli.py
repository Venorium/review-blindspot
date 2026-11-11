"""Offline CLI. Providers and arbitrary reviewer code are never executed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .demo import run_demo
from .fixtures import verify_all
from .exchange import wrap_review
from .io import ROOT, RBSError, read_json, write_json
from .packets import plan, prepare
from .quickstart import format_quickstart, quickstart
from .report import write_report
from .store import export_grading_packets, import_adjudication, import_submission
from .status import format_status, run_status
from .transport import format_summary, progress_to_stderr, review_jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m rbs', description='Review Blind Spot - offline-first experiment starter')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('quickstart', help='Try a guided offline demo; no API key or path choices needed')
    p.add_argument('--out', type=Path, help='New workspace outside the repository (default: system temporary directory)')
    p.add_argument('--json', action='store_true', help='Print paths and summary as JSON instead of guided text')
    p = sub.add_parser('status', help='Inspect run progress and integrity without changing it')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--json', action='store_true', help='Print structured diagnostics (errors on stderr)')
    p = sub.add_parser('plan', help='Count jobs and output-token caps without calling providers')
    p.add_argument('--config', type=Path, default=ROOT / 'configs/pilot.json')
    p = sub.add_parser('verify-fixtures', help='Execute only bundled trusted fixtures; not a sandbox')
    p.add_argument('--out', type=Path)
    for name in ('prepare','demo'):
        p = sub.add_parser(name, help='Export fresh isolated-input jobs' if name == 'prepare' else 'Run a scripted synthetic plumbing demonstration, without models')
        p.add_argument('--config', type=Path, default=ROOT / ('configs/smoke.json' if name == 'demo' else 'configs/pilot.json'))
        p.add_argument('--run', type=Path, required=True)
        p.add_argument('--packets', type=Path, required=True)
    for name in ('import-review','adjudicate'):
        p = sub.add_parser(name, help='Validate and append one immutable result')
        p.add_argument('--run', type=Path, required=True)
        p.add_argument('--file', type=Path, required=True)
    for name in ('report','grading-packets'):
        p = sub.add_parser(name, help='Export an immutable derived artifact')
        p.add_argument('--run', type=Path, required=True)
        p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('wrap-review', help='Bind a review and execution metadata to one packet; no provider call')
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--execution', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('review', help='Send prepared jobs to a declared transport (Ollama or a command); dry run unless confirmed')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--transport', type=Path, required=True, help='Transport JSON mapping model keys to backends')
    p.add_argument('--confirm-jobs', type=int, help='Exact number of reviews to send; omit for a dry run')
    p.add_argument('--limit', type=int, help='Send at most this many pending jobs (manifest order)')
    p.add_argument('--workers', type=int, default=1, help='Concurrent requests (latency then includes contention)')
    p.add_argument('--retry-interrupted', action='store_true', help='Re-attempt jobs whose first attempt left no record; logged as a new attempt')
    p.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'quickstart':
            result = quickstart(args.out)
            if not args.json:
                print(format_quickstart(result))
                return 0
        elif args.command == 'status':
            result = run_status(args.run)
            if not args.json:
                print(format_status(result))
                return 0
        elif args.command == 'plan':
            result = plan(read_json(args.config))
        elif args.command == 'verify-fixtures':
            result = verify_all()
            if args.out:
                write_json(args.out, result)
            print(json.dumps({'ok':result['ok'],'pairs':result['pairs'],'out':str(args.out) if args.out else None},indent=2))
            return 0 if result['ok'] else 1
        elif args.command == 'wrap-review':
            result = wrap_review(args.packet, args.review, args.execution, args.out)
        elif args.command == 'review':
            result = review_jobs(args.run, args.transport, confirm_jobs=args.confirm_jobs, limit=args.limit,
                                 workers=args.workers, retry_interrupted=args.retry_interrupted,
                                 progress=None if args.json else progress_to_stderr)
            if not args.json:
                print(format_summary(result))
                return 0
        elif args.command == 'prepare':
            result = prepare(read_json(args.config), args.run, args.packets)
        elif args.command == 'demo':
            result = run_demo(read_json(args.config), args.run, args.packets)
        elif args.command == 'import-review':
            result = {'stored':str(import_submission(args.run, read_json(args.file)))}
        elif args.command == 'adjudicate':
            result = {'stored':str(import_adjudication(args.run, read_json(args.file)))}
        elif args.command == 'grading-packets':
            result = export_grading_packets(args.run, args.out)
        else:
            result = write_report(args.run, args.out)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (RBSError, OSError, KeyError, TypeError, UnicodeError) as exc:
        if args.command == 'status' and args.json:
            print(json.dumps({'state': 'invalid_artifacts', 'error': str(exc)}), file=sys.stderr)
        else:
            print(f'ERROR: {exc}',file=sys.stderr)
        return 2
