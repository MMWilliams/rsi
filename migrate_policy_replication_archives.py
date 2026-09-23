"""Preserve nested replication banks while restoring legacy bank-read compatibility."""

from pathlib import Path

from rsi.common import write_json
from rsi.retention_run import seal_artifacts


for root in sorted(Path("runs").glob("policy-replication-v13-*")):
    nested_path = root / "protected_banks.json"
    if not nested_path.exists():
        continue
    nested = __import__("json").loads(nested_path.read_text(encoding="utf-8"))
    if not all(isinstance(value, dict) and "tasks" in value for value in nested.values()):
        continue
    write_json(root / "replication_banks.json", nested)
    write_json(root / "protected_banks.json", {"seed_" + str(seed): value["tasks"] for seed, value in nested.items()})
    write_json(root / "schema-migration.json", {"type": "replication-bank-view-v1", "original": "protected_banks.json", "preserved_as": "replication_banks.json"})
    seal_artifacts(root)
