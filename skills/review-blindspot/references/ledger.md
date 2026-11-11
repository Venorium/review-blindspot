# Ledger format v1

`snapshot.json` is the captured scope. Preserve it. `review.json` is the editable record;
its `snapshot_id` binds it to that capture. The helper never reads a review reference as
a command. It stores filenames and hashes, not a copy of the source or Git diff.

Set `reviewer_context` to `same_session` or `fresh_session` based on what actually happened.
Keep every captured path exactly once in `files`. Choose `unreviewed`, `reviewed`, or
`excluded`; reviewed and excluded paths require a concise `reason` explaining scope.

Each check has exactly these fields:

```json
{
  "id": "C1",
  "claim": "A token is inactive at its exact expiration time, per SPEC.md.",
  "files": ["expiry.py"],
  "status": "contradicted",
  "evidence": [
    {
      "kind": "inspection",
      "reference": "expiry.py:2 and SPEC.md:4",
      "observation": "The >= comparison accepts equality; the contract requires now < expires_at.",
      "sha256": null
    }
  ]
}
```

This is a format example, not a finding to copy into unrelated reviews. A concrete
counterexample can contradict a claim; one supported claim cannot establish all behavior.

Statuses: `unverified`, `supported`, `contradicted`, `inconclusive`. Supported and
contradicted checks without evidence remain gaps. `inspection` requires a reference and
observation, with `sha256: null`; the snapshot already binds the captured code.

For `test` evidence, `reference` is a file relative to the review directory, such as
`evidence/expiry-test.log`, and `sha256` is that file's actual SHA-256. A missing, changed,
or escaping log is an error. The helper verifies bytes, not the truth of a log's contents.
Never relabel a planned test as executed. Never invent output or a hash.

The helper emits:

| State | Meaning |
| --- | --- |
| `stale` | Scope, base/HEAD or captured file bytes/modes changed. Reassess a new capture. |
| `attention_required` | At least one claim is recorded as contradicted. Read its evidence. |
| `incomplete` | Unreviewed/excluded files, missing checks/evidence, or unresolved claims. |
| `documented` | Current recorded scope has supported checks; no gap was recorded. Not approval. |
| `no_changes` | Git comparison has no captured changed paths. No substantive review performed. |

## Boundaries

- Git must have an existing commit. `--base` compares directly to a commit/ref, not
  implicitly to a merge-base. Renames appear as deletion/addition; deletions can be reviewed.
- Non-ignored untracked files are included. Ignored files and unchanged dependencies
  are outside automatic capture; record their relevance in observations and limitations.
- Filters, external diff/text converters and fsmonitor are disabled. A repository using
  content filters may consequently show additional changes; do not silently dismiss them.
- Symbolic links and directory changes remain unsupported gaps. Every base/index submodule
  is explicitly a gap, even if unchanged; its repository is never traversed. Source bytes
  are never executed. Capture is limited to 2000 paths and 256 MiB of changed file contents.
- The working tree is not locked. Capture checks twice; finish edits before capturing and
  recheck immediately before delivering. An edit after the final check can invalidate it.
- Hashes are integrity checks, not signatures. A user able to rewrite the capture and
  ledger can rewrite their claims. The tool cannot certify semantic coverage or truth.
- Temporary directories may be cleaned by the OS. Use `--out` to retain review artifacts.
  Do not commit sensitive filenames or logs without reviewing them.
