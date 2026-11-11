"""Compare a recomputed metrics.json with a published one. Exit 1 on any difference."""
import argparse
import json
from pathlib import Path


def differences(a, b, path="$"):
    if type(a) is not type(b):
        return [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, dict):
        out = [f"{path}.{k}: missing on one side" for k in sorted(a.keys() ^ b.keys())]
        for k in sorted(a.keys() & b.keys()):
            out += differences(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--recomputed", type=Path, required=True)
    args = parser.parse_args()
    found = differences(json.loads(args.published.read_text(encoding="utf-8")),
                        json.loads(args.recomputed.read_text(encoding="utf-8")))
    print(json.dumps({"identical": not found, "differences": found[:50]}, indent=2))
    return 0 if not found else 1


if __name__ == "__main__":
    raise SystemExit(main())
