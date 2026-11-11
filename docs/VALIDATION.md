# What has been verified

This page records checks that were actually run, and what they do not cover.

## Continuous integration

Every push runs the offline suite on Linux, Windows and macOS with Python 3.11 and 3.14:
unit, integration and refutation tests; release hygiene (`tools/prepublish_check.py`);
both fixture corpora; the scripted demo; the skill walkthrough; recomputation of every
published pilot report from its raw records (`tools/reproduce_reports.py`, which requires
identical metrics); and an editable install of the `rbs` command.

The first hosted run found a real reproducibility issue: Python 3.12 changed how `sum()`
adds floats, so a published latency total differed between Python 3.11 and 3.14. Float
totals now use `math.fsum`, which is exact; the published values did not change.

## Agent integration (10 November 2026)

With isolated agent configurations (temporary `CODEX_HOME` and `CLAUDE_CONFIG_DIR`):

| Check | Result |
| --- | --- |
| `claude plugin validate .` | Passed |
| Claude Code: marketplace from GitHub, then install | Installed 0.2.0; one skill, no agent, hook or MCP server; about 73 always-on tokens |
| Codex CLI 0.159.3: `codex plugin marketplace add Venorium/review-blindspot`, then `codex plugin add` | Installed 0.2.0 |
| Codex app-server `skills/list` after plugin install | `review-blindspot:review-blindspot` listed and enabled |
| Codex app-server `skills/list` after the per-project installer | `review-blindspot` listed and enabled with its display name and prompt |

No model turn was started by these checks. They verify installation and discovery, not
how a model uses the skill.

## Pilots

Each pilot plan was frozen before its first request and copied into the run. Raw requests,
responses, judgments and reports are published under [results/](../results/README.md) and
recomputed in CI. Before publication, the runs were redacted for privacy only (local
directory paths, and frozen copies of internal planning documents); each redaction is
listed with the original hashes in the run's `PUBLICATION_REDACTION.json`.
The frozen code in each run is the exact code that ran and stays untouched, so its
`quickstart` message still names an onboarding note that is not published.

## Not verified

Human audit of the LLM judgments; independent review of corpus v2; hosted or larger
models; behaviour of a model invoking the skill; submission to a public plugin directory.
