"""V82 audit entry point using the versioned lineage replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_credit_lineage_v80 import audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
