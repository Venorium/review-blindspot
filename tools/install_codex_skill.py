"""Install the self-contained Agent Skill into a project for Codex and/or Claude Code.

Codex reads project skills from .agents/skills/; Claude Code reads .claude/skills/.
The SKILL.md follows the open Agent Skills format, so the same four files serve both.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'skills/review-blindspot'
FILES = ('SKILL.md', 'agents/openai.yaml', 'scripts/review_blindspot.py', 'references/ledger.md')
HOSTS = {'codex': ('.agents', 'skills'), 'claude': ('.claude', 'skills')}
NEXT = {'codex': 'Open a new Codex chat in this project and invoke $review-blindspot.',
        'claude': 'Start Claude Code in this project and ask for /review-blindspot (or describe a pre-commit review).'}


def install(project, host='codex'):
    if host not in HOSTS:
        raise ValueError('Unknown host; choose codex or claude')
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be an existing directory')
    top, sub = HOSTS[host]
    parent = project / top / sub
    for part in (project / top, parent):
        if part.is_symlink() or not part.resolve().is_relative_to(project):
            raise ValueError('Skill directories must stay inside the selected project')
    destination = parent / 'review-blindspot'
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Skill already exists; no files overwritten: ' + str(destination))
    payload = {}
    for name in FILES:
        path = SOURCE / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or linked skill resource: ' + name)
        payload[name] = path.read_bytes()
    parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the destination; only this newly created staging directory is removed on failure.
    stage = Path(tempfile.mkdtemp(prefix='.rbs-install-', dir=parent))
    try:
        for name, content in payload.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError('Skill destination appeared during installation')
        stage.rename(destination)
    finally:
        if stage.exists():
            if stage.is_symlink() or stage.resolve().parent != parent.resolve():
                raise ValueError('Refusing to clean a staging path outside the skill directory')
            shutil.rmtree(stage)
    return {'host': host, 'installed': str(destination), 'files': {name: hashlib.sha256(data).hexdigest()
            for name, data in payload.items()}, 'next': NEXT[host]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--host', choices=('codex', 'claude', 'all'), default='codex',
                        help='Agent that will load the skill (default: codex)')
    args = parser.parse_args()
    hosts = list(HOSTS) if args.host == 'all' else [args.host]
    try:
        project = Path(args.project).resolve(strict=True)
        existing = [h for h in hosts if (project / HOSTS[h][0] / HOSTS[h][1] / 'review-blindspot').exists()]
        if existing:
            raise FileExistsError('Skill already installed for: ' + ', '.join(existing) + '; no files written')
        print(json.dumps([install(project, host) for host in hosts], indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
