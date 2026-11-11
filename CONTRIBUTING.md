# Contributing

Start with the [research protocol](research/PROTOCOL.md) and the [roadmap](research/ROADMAP.md). Changes should identify one measurement
or usability problem, add a failing test where applicable, and preserve existing results.
Do not introduce a provider SDK, UI or framework without an explicit experimental need.

New cases need provenance, sufficient visible specifications, paired variants, visible
checks and a separate executable witness. A false assertion is a target failure; syntax
errors, missing dependencies and skipped tests are infrastructure errors. Cases derived
from the same issue remain in the same family and split. Never tune on a held-out set.

Run `python -m unittest discover -s tests -v`, `python -m rbs verify-fixtures` and
`python tools/prepublish_check.py`. Report environment and actual outcomes. Published runs
are historical records: add a new run instead of editing one to imply it tested new code.
All model or adjudicator simulation must be labelled. Do not present model-generated
judgments as human annotations or claim a review was independent without isolation evidence.
