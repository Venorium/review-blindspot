"""Small, strict artifact helpers. Hashes provide integrity, not authenticity."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 2_000_000

class RBSError(ValueError):
    """Actionable validation error exposed by the CLI."""

def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RBSError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result

def _no_constant(value: str) -> None:
    raise RBSError(f"Non-finite JSON constant is forbidden: {value}")

def read_json(path: Path) -> Any:
    if path.is_symlink():
        raise RBSError(f"Refusing a symbolic-link JSON file: {path}")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise RBSError(f"JSON exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RBSError(f"Invalid UTF-8 JSON in {path}: {exc}") from exc

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path: Path, value: Any, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    # Exclusive creation prevents silently replacing experimental evidence.
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)

def keys(obj: Any, required: set[str], optional: set[str] | None = None) -> None:
    if not isinstance(obj, dict):
        raise RBSError("Expected a JSON object")
    optional = optional or set()
    missing, extra = required - obj.keys(), obj.keys() - required - optional
    if missing or extra:
        raise RBSError(f"Object fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")

def text(value: Any, label: str, *, maximum: int = 10000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise RBSError(f"{label} must be a nonempty string of at most {maximum} characters")
    return value

def integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise RBSError(f"{label} must be an integer >= {minimum}")
    return value

def nonnegative_or_none(value: Any, label: str, *, integer_only: bool = False) -> None:
    if value is None:
        return
    if integer_only:
        integer(value, label)
    elif type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise RBSError(f"{label} must be null or a finite nonnegative number")

def nested(a: Path, b: Path) -> bool:
    """True when either resolved path is inside the other, including equality."""
    a, b = a.resolve(), b.resolve()
    return a == b or a in b.parents or b in a.parents
