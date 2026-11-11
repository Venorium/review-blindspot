"""Release hygiene checks run before publishing and in CI. Standard library only.

Checks community files, version consistency, pinned GitHub Actions, byte-exact
attributes for hashed records, relative Markdown links, large files, common secret
patterns, tracked files that .gitignore marks as local-only, personal paths and email
addresses, and French prose outside published runs (the documentation is English).

Maintainers can add private terms that must never be published (names, local folders)
without writing them into the repository: one case-insensitive regular expression per
line in .git/info/private-terms, or in the file named by RBS_PRIVATE_TERMS. Lines
starting with # are comments.

Exit 0 when clean, 1 with a JSON list of problems otherwise.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SELF = ("tools/prepublish_check.py", "tests/test_prepublish_check.py")  # contain sample patterns
REQUIRED = ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "CITATION.cff",
            "CHANGELOG.md", "pyproject.toml", ".github/workflows/tests.yml", ".github/dependabot.yml"]
SECRETS = [re.compile(p) for p in (r"gh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{40,}",
                                   r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}", r"sk-ant-[A-Za-z0-9_-]{30,}",
                                   r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
                                   r"xox[baprs]-[A-Za-z0-9-]{20,}")]
FROZEN_RUN = re.compile(r"^results/[^/]+/run/")
# A drive-letter or POSIX path into a user profile. JSON escapes such as "a:\n" are not paths.
PROFILE_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:(?:\\\\|\\(?![ntrbu\"\\/])|/)+(?:[Uu]sers|USERS|Documents and Settings)\b"
                          r"|(?<![\w.])/(?:home|Users)/[A-Za-z][\w.-]*/")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
ALLOWED_EMAIL_DOMAINS = ("users.noreply.github.com", "example.invalid", "example.com", "example.org")
FRENCH = re.compile(r"\b(les|des|une|est|pour|avec|dans|sont|cette|qui|nous|vous|aux|sur|pas|être|été|mais|leur|très)\b",
                    re.I)
PROSE_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".cff", ".json", ".txt"}


def git_list(*args: str) -> list[str] | None:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", *args], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [n for n in out.decode("utf-8").split("\0") if n]


def files() -> list[Path]:
    names = git_list("--cached", "--others", "--exclude-standard")
    if names is None:
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()]
    return [ROOT / n for n in names if "__pycache__" not in n and (ROOT / n).is_file()]


def private_terms() -> list[re.Pattern]:
    source = os.environ.get("RBS_PRIVATE_TERMS")
    path = Path(source) if source else ROOT / ".git" / "info" / "private-terms"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [re.compile(line.strip(), re.I) for line in lines if line.strip() and not line.lstrip().startswith("#")]


def anchors(path: Path) -> set[str]:
    found, counts = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", re.sub(r"(?ms)^\x60{3}.*?^\x60{3}", "", path.read_text(encoding="utf-8")), re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        found.add(slug + (f"-{n}" if n else ""))
    return found


def check_links(path: Path, rel: str, content: str, problems: list[str]) -> None:
    body = re.sub(r"(?ms)^\x60{3}.*?^\x60{3}", "", content)
    refs = re.findall(r"\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", body) + re.findall(r'(?:href|src|srcset)="([^"]+)"', body)
    for ref in refs:
        parsed = urlsplit(ref.strip("<>"))
        if parsed.scheme or parsed.netloc or ref.startswith("mailto:"):
            continue
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if not target.exists():
            problems.append(f"broken link in {rel}: {ref}")
        elif parsed.fragment and target.suffix == ".md" and unquote(parsed.fragment) not in anchors(target):
            problems.append(f"broken anchor in {rel}: {ref}")


def check() -> tuple[list[str], int]:
    problems = []
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            problems.append(f"missing {name}")
    sys.path.insert(0, str(ROOT))
    from rbs import __version__ as version
    versions = {"CITATION.cff": re.search(r'^version:\s*"?([^"\n]+)"?', (ROOT / "CITATION.cff").read_text(encoding="utf-8"), re.M),
                "plugin.json": json.loads((ROOT / "plugin.json").read_text(encoding="utf-8")).get("version"),
                ".codex-plugin/plugin.json": json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")).get("version"),
                "SKILL.md": re.search(r'^\s+version:\s*"([^"]+)"', (ROOT / "skills/review-blindspot/SKILL.md").read_text(encoding="utf-8"), re.M)}
    for name, value in versions.items():
        value = value.group(1) if isinstance(value, re.Match) else value
        if value != version:
            problems.append(f"version mismatch: {name} has {value!r}, rbs has {version!r}")
    if f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        problems.append(f"CHANGELOG.md has no entry for {version}")
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        for ref in re.findall(r"uses:\s*([^\s#]+)", workflow.read_text(encoding="utf-8")):
            if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref):
                problems.append(f"{workflow.name}: action not pinned to a commit SHA: {ref}")
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("results/** -text", "docs/examples/** -text"):
        if pattern not in attributes:
            problems.append(f".gitattributes lacks '{pattern}' (hashed records must stay byte-exact)")
    local_only = set(git_list("--cached", "--ignored", "--exclude-standard") or [])
    for rel in sorted(local_only):
        problems.append(f"tracked file is marked local-only by .gitignore: {rel}")
    terms = private_terms()
    for path in files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in local_only:
            continue
        if path.stat().st_size > 5_000_000:
            problems.append(f"large file over 5 MB: {rel}")
        data = path.read_bytes()
        if b"\0" in data[:4096]:
            continue
        content = data.decode("utf-8", "replace")
        for pattern in SECRETS:
            if pattern.search(content):
                problems.append(f"possible secret ({pattern.pattern[:18]}...) in {rel}")
        if PROFILE_PATH.search(content):
            problems.append(f"personal path in {rel}: {PROFILE_PATH.search(content).group(0)}")
        for address in sorted(set(EMAIL.findall(content))):
            if not address.lower().endswith(ALLOWED_EMAIL_DOMAINS):
                problems.append(f"email address in {rel}: {address}")
        if rel not in SELF:
            for term in terms:
                if term.search(content):
                    problems.append(f"private term #{terms.index(term) + 1} in {rel}")
            if not rel.startswith("results/") and path.suffix in PROSE_SUFFIXES:
                words = {w.lower() for w in FRENCH.findall(content)}
                if len(words) >= 3:
                    problems.append(f"French prose in {rel} (documentation is English): {', '.join(sorted(words))}")
        if path.suffix == ".md" and not FROZEN_RUN.match(rel):
            check_links(path, rel, content, problems)
    return problems, len(terms)


def main() -> int:
    problems, terms = check()
    print(json.dumps({"ok": not problems, "private_terms_checked": terms, "problems": problems}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
