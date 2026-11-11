# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [semantic versioning](https://semver.org/).

## [0.2.0] — 2026-11-10

### Added

- `rbs review`: sends prepared jobs to a declared transport, either an Ollama endpoint
  (text only, stateless, structured output, enforced output cap, per-job seed) or any
  command that reads the prompt on stdin. Dry run by default, exact `--confirm-jobs` gate,
  resumable, no silent retry, raw request/response kept and hashed, model digests frozen.
- Pilot A: 300 local reviews by gpt-oss:20b, qwen3.6:35b and gemma4:26b on the 15
  development pairs, plan frozen before the first request. Result: a ceiling (every
  defect identified, no control blocked, in every protocol). Raw records, LLM-judged
  adjudications and reports in `results/pilot-2026-11-10`.
- Corpus v2 (`fixtures-v2/`, 10 harder pairs: omissions, cross-function effects, iterator,
  rounding, stability, Unicode, retry, calendar, path and deduplication edge cases) and
  pilot B on it (200 reviews), frozen before any model saw it. Result: every defect
  identified again, but 12 of 91 valid control reviews blocked by one model, mostly for the
  same invented requirement in independent samples; any-block panels rejected 3 of 10
  correct changes against 1 of 10 for one reviewer (`results/pilot-2026-11-10-v2`).
- `corpus` key in run configurations and `verify-fixtures --corpus`.
- Reports gain a "Shared misses between reviewers" table and a `provenance.json` naming
  the computing code and any difference from the code frozen in the run.
- `rbs adjudicate` accepts a JSONL batch, validated in full before anything is stored.
- Plugin marketplaces for Codex (`.agents/plugins`) and Claude Code (`.claude-plugin`), so
  the skill installs straight from GitHub in both agents; installer `--host codex|claude|all`
  for a per-project copy.
- `tools/render_blindspot_map.py` (per-case, per-reviewer SVG map), `tools/analyze_run.py`
  (reviewer-level descriptives) and `tools/prepublish_check.py` (release hygiene).
- `tools/redact_run.py`: one-time publication redaction of a finished run (local paths,
  selected frozen documents). It re-seals the manifest, records every removal with its
  original hash and refuses any change to the metrics.
- Packaging (`pyproject.toml`, `rbs` console script), citation metadata, code of conduct,
  issue and pull-request templates, Dependabot for pinned GitHub Actions.

### Changed

- CI runs on Linux, Windows and macOS with Python 3.11 and 3.14, pins actions by commit
  and recomputes the published pilot report from its raw records.
- Published runs and examples are excluded from line-ending normalization so their
  hashes verify on every platform.
- Release hygiene also rejects tracked local-only files, personal paths, email addresses
  other than placeholders and no-reply addresses, and French prose outside published runs.

## [0.1.0] — 2026-10-04

### Added

- Offline harness: paired fixtures, frozen runs, strict imports, adjudication, bounded
  metrics, reports, `quickstart` and `status`.
- Codex skill `review-blindspot` with an evidence ledger and freshness check.

[0.2.0]: https://github.com/Venorium/review-blindspot/releases/tag/v0.2.0
[0.1.0]: https://github.com/Venorium/review-blindspot/releases/tag/v0.1.0
