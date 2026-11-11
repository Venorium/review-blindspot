# Transport interface

The core is provider-independent. `rbs review` implements the transport for two backends:
an **Ollama** server (local or remote; text only, stateless request, structured output,
output cap enforced through `num_predict`, a seed per job) and any **command** that reads the
prompt on stdin and prints the review object (`codex exec`, another CLI, a custom script).
Examples: `configs/transport.ollama-pilot.json` and `configs/transport.EXAMPLE.json`.
A chat subscription is not API credit; check what you actually have access to.

```bash
python -m rbs prepare --config configs/smoke.json --run runs/pilot-001 --packets ../rbs-pilot-packets-001
python -m rbs review --run runs/pilot-001 --transport configs/transport.ollama-pilot.json        # dry run: nothing is sent
python -m rbs review --run runs/pilot-001 --transport configs/transport.ollama-pilot.json --confirm-jobs 16
```

Nothing is sent unless `--confirm-jobs` equals the exact number of reviews to send. Model
identities (Ollama digest, server or client version) are frozen in
`<run>/transport/transport.json` before the first request; changing the configuration or a
model during a run is refused. Each attempt keeps the exact request, the raw response and
their hashes in `<run>/transport/raw/`, plus a line in `attempts.jsonl`. A failure, a
truncated output or non-conforming JSON is imported as such (`timeout`, `provider_error`,
`invalid_output`), never converted into an approval and never retried. An interrupted
attempt with no result is re-sent only with `--retry-interrupted`, as attempt 2.

A command starts in an empty temporary directory that contains only the schema
(`{schema_path}`); the prompt arrives on stdin. An agent CLI still keeps its tools, user
configuration and disk access, so `isolation_attested` stays `false` unless isolation is
actually enforced and documented. The Ollama transport sends only the packet bytes, with no
tool, and is attested as such; that says nothing about training data.

## Minimal manual circuit

The orchestrator prepares a run and keeps its manifest private. For one job it picks the
logical model from the manifest and builds a fresh request from review_prompt.txt,
SPEC.md, before.py, candidate.py, patch.diff, test_public.py and review.schema.json, plus
AUTHOR_NOTE.md only if the packet contains it. The text-only track has no tools, browsing
or file access. Never send job.json as an instruction: it only binds artifacts.

The model output is the `review` object, not the execution envelope. Save raw transport
bytes separately and extract the object without rewriting it. Execution metadata comes from
the client or provider, never from the model. Unknown values stay null. Fill
`examples/execution.TEMPLATE.json` in another location; no secret key is needed.

Bind a review to one packet (replace JOB_ID with the prepared identifier):

```bash
python -m rbs wrap-review --packet ../rbs-pilot-packets-001/JOB_ID --review ../submissions/review.json --execution ../submissions/execution.json --out ../submissions/submission.json
python -m rbs import-review --run runs/pilot-001 --file ../submissions/submission.json
```

Keep submissions separate from inputs. For a failed call, the review is `null` and the
execution status is `timeout`, `provider_error` or `invalid_output`. A failed call's cost
may still be known and should be recorded.

## Judgment and report

```bash
python -m rbs grading-packets --run runs/pilot-001 --out ../rbs-grading-packets-001
python -m rbs adjudicate --run runs/pilot-001 --file ../adjudications/annotations.jsonl
python -m rbs report --run runs/pilot-001 --out runs/pilot-001/report-001
```

Grading packets cover blocking reviews and hide model and arm. A report can be produced
before completion: missing jobs and unjudged targets stay explicitly undetermined. Mock
annotations are refused in external runs, and an external report is never labelled as
validated evidence automatically.

## Requirements before real automation

One fresh request or session per job; frozen model and parameters; no shared messages; no
global prefix containing answer keys; executed order and timestamps kept; real limits
checked; raw request and response saved; explicit errors; a preregistered retry policy;
careful rate; a truly bounded total budget. Exported caps and `isolation_attested` are only
declarations when nothing enforces them.

For a tool-using agent CLI, an instruction such as "do not read other files" is not
isolation. Restrict mounts and permissions, never mount the folder holding all jobs, and
neutralize inherited project context or shared memory before calling a review blind.

## Covered failure tests

`tests/test_transport.py` covers, with a fake Ollama server and a fake command: success;
dry run; timeout; HTTP error; output cut at the cap; malformed JSON; object violating the
contract; changed configuration or model; missing model; interrupted attempt; double
import; refused demo run; empty working directory for commands; no answer key or job ID in
the prompt. Still to cover with a real provider: billed usage, server-side session reuse
and rate limits.
