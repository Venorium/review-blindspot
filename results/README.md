# Published runs

| Run | Corpus | Reviews | Result |
| --- | --- | --- | --- |
| [Pilot A](pilot-2026-11-10/README.md) | v1, 15 development pairs | 300 | Ceiling: every defect identified, no control blocked, in all four protocols |
| [Pilot B](pilot-2026-11-10-v2/README.md) | v2, 10 harder pairs | 200 | Every defect identified; 12 of 91 valid control reviews blocked, all by one model, mostly for the same invented requirement; any-block panels rejected 3 of 10 correct changes against 1 of 10 for one reviewer |

Each run folder keeps the frozen configuration, code, corpus and plan (`run/frozen/`), every
request and raw response with hashes (`run/transport/`), the imported reviews and
judgments, and a report with its provenance. Records are write-once: a correction becomes
a new run, never an edit. Recompute any report without a model:

```bash
python -m rbs report --run results/<run>/run --out ../recomputed-report
python tools/check_reproduction.py --published results/<run>/run/report/metrics.json --recomputed ../recomputed-report/metrics.json
```
