from __future__ import annotations

import hashlib
import json
import datetime
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "trapdoor-loom"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Journal:
    """Host-owned hash chain: corruption is detectable, not cryptographically authenticated."""

    def __init__(self, path: Path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite journal: {path}")
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.previous = "0" * 64
        self.count = 0

    def append(self, kind: str, payload: dict) -> str:
        row = {"seq": self.count, "previous": self.previous, "kind": kind, "payload": payload,
               "schema_version": 2, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        row["sha256"] = digest(row)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.previous = row["sha256"]
        self.count += 1
        return row["sha256"]


def verify_journal(path: Path) -> int:
    previous = "0" * 64
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        actual = row.pop("sha256")
        if row["previous"] != previous or row["seq"] != count or digest(row) != actual:
            raise ValueError(f"Broken journal chain at event {count}")
        previous = actual
        count += 1
    return count
