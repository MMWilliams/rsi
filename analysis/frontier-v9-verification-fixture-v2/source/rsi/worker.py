"""Line-oriented worker. It never receives reference programs or hidden examples."""
from __future__ import annotations

import json
import sys

from .search import solve


def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if set(request) != {"tasks", "config", "budget", "max_atoms", "macros", "proposals"}:
                raise ValueError("Invalid request fields")
            rows = [solve(task, request["config"], request["budget"], request["max_atoms"], request["macros"], request["proposals"].get(task["id"], [])) for task in request["tasks"]]
            response = {"results": rows}
        except Exception as exc:
            response = {"error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(response, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
