# Use Review Blind Spot in Codex or Claude Code

**Turn a code review into a current, inspectable evidence record.** Ask your agent to review
your changes; see what was inspected, what supports each claim, what is still unknown,
and whether the code has changed since the review began.

This is a local skill in the open [Agent Skills](https://agentskills.io) format, with a
deterministic Python helper. The agent supplies the reasoning.
The helper supplies capture, consistency checks and report generation. No MCP service,
API key, pip installation or additional model call is required by the helper. A review
uses your normal Codex or Claude Code account and usage allowance.

## Install once per project

Prerequisites: Python 3.11+, Git, and Codex or Claude Code with local skills support. Download this
repository, then from its root run:

```text
python tools/install_codex_skill.py --project /absolute/path/to/your-project
```

Add `--host claude` for Claude Code (`.claude/skills/`) or `--host all` for both agents.

The existing target directory receives `.agents/skills/review-blindspot/` (Codex) and/or
`.claude/skills/review-blindspot/` (Claude Code). The installer
copies four self-contained files, checks destination boundaries and refuses an existing
skill. It leaves agent instruction files, agent configuration and other skills unchanged. Review the
files before committing this project-local installation; keep them out of the change
you intend to review. No link back to this checkout is needed after installation.

Open a new Codex chat **in the target project** and send:

```text
$review-blindspot Review my changes before commit. Show concrete findings,
the supporting evidence, and anything still unverified.
```

The request can be written in any language; the agent answers in the same language.

In Claude Code, start a session in the project and type `/review-blindspot` followed by
the same request, or simply ask for a pre-commit review with evidence and gaps.

If the skill is absent from the picker, confirm its `SKILL.md` path and open a new chat;
restart the client if it still has a stale skill list. The target repository needs an
existing commit and no unresolved merge conflicts for capture. The installer itself
does not initialize Git. Remove only the installed skill folder to uninstall it; update
by retaining the old folder elsewhere before installing, since there is no forced overwrite.

## What you get

| During a review | Observable result |
| --- | --- |
| A changed file has no review record | `incomplete`, with the missing path. |
| A claim is marked supported without evidence | `incomplete`, with the claim ID. |
| A recorded counterexample contradicts a claim | `attention_required`; inspect the evidence. |
| A saved test log is altered or missing | Error, not a successful check. |
| Code, base/HEAD or the captured scope changes | `stale`; the earlier review remains available. |
| Current scope has complete supported records | `documented`, which is not approval. |

Codex reads the requested change and fills a small ledger. Each claim references captured
files and either source inspection or a saved test result. The helper validates structure,
hashes, recorded coverage and freshness; it cannot judge whether reasoning or logs are true.
Test execution is separate and subject to the target project's permissions and isolation.

The default comparison is the current working tree versus `HEAD`, including non-ignored
untracked files. `--base <commit-or-ref>` selects another comparison; for branch divergence,
choose the intended merge-base explicitly. Index-only states cancelled in the working tree
are outside this comparison. Unsupported links/submodules stay visible as gaps. See the
[ledger contract](../skills/review-blindspot/references/ledger.md) for limits and exit codes.

## Try the mechanics without a Codex request

```text
python tools/demo_codex_skill.py
```

The command creates a temporary Git repository, installs the skill and demonstrates
`incomplete → attention_required → stale`. It retains three reports and prints their paths.
The example is scripted, uses a trusted toy file, executes no project source and calls
no model. It demonstrates the mechanisms, not a gain in review accuracy.

[Open the constructed example report](examples/codex/REPORT.md).

## Why add this to Codex?

Codex already provides `/review`, prioritized findings and revision-specific viewed
markers. This project does not claim to invent those capabilities. The addition is a
portable ledger connecting each claim to evidence, exposing missing records, binding
saved logs to hashes and checking that its local capture still matches the code.
The same files can be inspected outside Codex. [Official code review documentation](https://learn.chatgpt.com/docs/code-review)

This skill can guide a normal chat; it does not intercept `/review`, enforce a merge gate,
or automatically export a native review. Freshness and missing-record checks are implemented
and tested. Whether the workflow finds more bugs, adds useful evidence, or costs too much
attention is still a user/model evaluation question.

## Packaging and verified compatibility

The repository is also a plugin marketplace for both agents: `.agents/plugins/marketplace.json`
with `.codex-plugin/plugin.json` for Codex, `.claude-plugin/marketplace.json` with
`.claude-plugin/plugin.json` for Claude Code, and a portable root `plugin.json`. The plugin
contains one skill, no MCP server and no hook.

```text
codex plugin marketplace add Venorium/review-blindspot
codex plugin add review-blindspot@review-blindspot
```

In Claude Code: `/plugin marketplace add Venorium/review-blindspot`, then
`/plugin install review-blindspot@review-blindspot`. Installed as a plugin, the skill is
named `review-blindspot:review-blindspot` in Codex. Installation from GitHub was verified in
both agents with isolated configurations, without starting a model turn; submission to a
public plugin directory has not been attempted. Details: [VALIDATION.md](VALIDATION.md).
Tests also exercise the installed helper in a separate Git repository.

Official sources checked on 4 October 2026:

- [Build skills](https://learn.chatgpt.com/docs/build-skills): project-local discovery and invocation.
- [Package your plugin](https://developers.openai.com/plugins/build/plugins): portable manifest and compatibility layout.
- [App Server](https://learn.chatgpt.com/docs/app-server): `skills/list` for discovery verification.

## Next proof of value

Before claiming better reviews, compare the normal review and this workflow on the same
preselected changes and contracts. Preserve findings, false alarms, missing evidence,
time and real usage; use separate review contexts without calling them independent.
Do not tune the skill against a later evaluation set. First usability target: a new
reader installs it, starts a review, finds an unresolved claim and understands a stale
report without maintaining JSON by hand. These targets are not achieved study results.
