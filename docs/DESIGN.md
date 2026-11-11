# Presentation and user experience

Primary audience: tool builders and research engineers discovering the repository on
GitHub. Goal: understand the question, try the software and read a result without
studying the whole protocol. The scientific contract stays in
[research/PROTOCOL.md](../research/PROTOCOL.md).

## References and how they were applied

| Primary source | Principle | Application |
| --- | --- | --- |
| [GitHub — About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) | Explain purpose, getting started and help; use relative links | One promise, results first, one-line installs, links to details |
| [GitHub — Writing quickstart](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github) | Images with alt text; the `picture` element | Local SVGs, compact variants, complete alt text |
| [Nielsen Norman Group — Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Essentials first, advanced options reachable | Results and install on top; troubleshooting collapsed; protocol separate |
| [Nielsen Norman Group — Aesthetic-usability effect](https://www.nngroup.com/articles/aesthetic-usability-effect/) | Visual appeal can hide usability problems | Check tasks and data, not only looks |
| [Command Line Interface Guidelines](https://clig.dev/) | Human-readable output, composable for scripts, next step visible | Text and JSON modes, errors on stderr, suggested commands never executed |

## Visual direction

Palette: slate blue `#10232e`, light text `#f6f8f5`, mint accent `#72dfb6`, amber accent
`#f1bd6c`. No meaning relies on colour alone: every map cell also carries a glyph. System
fonts only; no remote font, animation, telemetry or downloaded asset. Simulated results
are labelled inside the image and in the adjacent text, and reports remain readable as
text when images are not shown.

## Faithful figures

`docs/examples/` holds exact copies of a scripted demo's outputs. `tools/render_demo_preview.py`
draws the demo preview from that JSON and refuses external data; tests compare the stored
SVGs with their regeneration. `tools/render_blindspot_map.py` draws pilot maps from a run
through the harness's own integrity checks. Never edit a number inside an SVG: regenerate it.

## Remaining human criterion

With three new readers: after thirty seconds, explain what is measured and tell simulation
from real results; within five minutes of cloning, install the skill or run the demo, find
the report and diagnose an incomplete run. These are targets, not results already obtained.
