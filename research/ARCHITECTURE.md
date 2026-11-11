# Architecture and contracts

## Trust flow

The corpus builder reads everything and produces the cases. The preparer freezes the
state and exports only the allowed inputs. A reviewer receives a single packet. The
transport writes its answer to a separate location. The importer validates structure and
identity. The judge reads an anonymized view and produces an annotation. The reporter
computes measures without executing any response text.

Security does not come from named roles: it must be enforced by actual access controls.
The computation logic cannot grant operating-system permissions to a reviewer.

## Components

- `rbs.fixtures` loads a corpus and runs its assertions in separate processes.
- `rbs.packets` validates the plan, counts the work, freezes artifacts and separates inputs.
- `rbs.transport` sends one stateless request per job to Ollama or to a declared command.
- `rbs.schema` validates reviews and annotations: unknown fields, arbitrary paths,
  non-finite values and verdict/finding inconsistencies are rejected.
- `rbs.store` keeps at most one response and one annotation per job, with checksums.
- `rbs.metrics` defines outcomes and their denominators, independent of any provider.
- `rbs.report` writes Markdown, JSON, CSV and a provenance record.
- `rbs.demo` simulates outputs from the answer keys, only to exercise the pipeline.
- `rbs.status` diagnoses a run without changing it; `rbs.cli` exposes local commands.

Dependencies point to the core of contracts and artifacts, not to a provider. Metrics can
be tested with fabricated observations without calling a model. Import never calls the
judge; an unjudged blocking review stays undetermined for the target.

## Layout at run time

```text
workspace/
  review-blindspot/           # builder and assessor only
    fixtures/                 # visible answer keys: never give reviewers this folder
    research/
    runs/pilot-001/
      manifest.json
      manifest.sha256
      frozen/
      responses/
      adjudications/
      integrity/
      transport/              # frozen transport, raw requests and responses
  rbs-pilot-packets-001/
    job-opaque-a/             # the only input sent or mounted for one reviewer
    job-opaque-b/             # another context; never mount the parent folder
  rbs-grading-packets-001/    # judges only, never reviewers
```

The program refuses packets inside the repository or nested in the run, and checks the
exact content of a packet at import, including the absence of extra files. Reviewer
outputs must never be written into their input packets.

## Identifiers and immutability

Variants are named explicitly in the assessor corpus and anonymized in reviewer inputs.
The private manifest links job, case, family, variant, arm, slot and repetition; the job
list is shuffled. The packet hash binds a result to the bytes presented; it does not prove
that a transport actually sent them. `job.json` holds the hashes of the other packet files,
and the manifest also freezes `job.json`.

Append-only storage is a software contract. There is no WORM storage or third-party
signature. An interruption between writing a JSON record and its checksum yields a
rejected state, never an implicitly valid result.

## Model interface

The system consumes a review object and an execution envelope. Providers stay
replaceable. A transport extracts structured output and never invents metadata: timings,
model identities and token counts come from the transport, never from the reviewer's text.
See [adapters/README.md](../adapters/README.md).

## Non-functional requirements

Offline start with Python alone; explicit errors; no secrets in packets; no implicit paid
call; strict JSON; controlled paths; retained logs; small deterministic tests; textual
results; versioned formats; no metric based only on an uncalibrated LLM judge.

Execution limits apply to the trusted bundled fixtures only. Third-party pull requests
need an ephemeral sandbox with no network, no secrets, CPU/memory/process limits, minimal
mounts and observability. That sandbox is not provided.

## Extensions not to confuse with what exists

Total budget enforcement; multi-attempt retry policies; repetition plans with conditional
per-case analysis; length-matched neutral context controls; model-submitted executable
counterexamples in a sandbox; natural data and a held-out set; panels with communication;
double adjudication with inter-judge agreement. Each needs its own ticket, tests and an
explicit protocol change.
