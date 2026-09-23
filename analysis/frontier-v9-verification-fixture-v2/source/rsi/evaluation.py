from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from .banks import public_task
from .common import ROOT, canonical, digest
from .oracle import correct, outcomes


class Worker:
    def __init__(self):
        self.process = subprocess.Popen([sys.executable, "-m", "rsi.worker"], cwd=ROOT,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding="utf-8", bufsize=1,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.messages = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        for line in self.process.stdout:
            self.messages.put(line)
        self.messages.put(None)

    def request(self, payload):
        self.process.stdin.write(canonical(payload) + "\n")
        self.process.stdin.flush()
        try:
            line = self.messages.get(timeout=120)
        except queue.Empty:
            self.close()
            raise TimeoutError("Worker exceeded 120 seconds")
        if line is None:
            raise RuntimeError("Worker exited: " + self.process.stderr.read()[-2000:])
        result = json.loads(line)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["results"]

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdout, self.process.stderr):
            stream.close()


class Evaluator:
    def __init__(self, journal, config, worker):
        self.journal, self.config, self.worker = journal, config, worker
        self.ledger = {"worker_batches": 0, "search_expansions": 0, "primitive_executions": 0,
                       "model_proposal_checks": 0, "oracle_string_executions": 0, "replay_batches": 0, "wall_seconds": 0.0, "incidents": 0}
        self.sensor_files = [ROOT / "rsi" / name for name in ("oracle.py", "evaluation.py", "banks.py", "worker.py")]
        self.sensor_hashes = {str(path.relative_to(ROOT)): digest(path.read_text(encoding="utf-8")) for path in self.sensor_files}

    def assert_integrity(self):
        current = {str(path.relative_to(ROOT)): digest(path.read_text(encoding="utf-8")) for path in self.sensor_files}
        if current != self.sensor_hashes:
            raise RuntimeError("Protected code changed during run")

    def evaluate(self, tasks, search_config, label, macros=(), proposals=None, replay=True):
        self.assert_integrity()
        request = {"tasks": [public_task(task) for task in tasks], "config": search_config,
                   "budget": self.config["search_budget"], "max_atoms": self.config["max_atoms"],
                   "macros": list(macros), "proposals": proposals or {}}
        ledger_before = dict(self.ledger)
        started = time.perf_counter()
        results = self.worker.request(request)
        self.ledger["worker_batches"] += 1
        if replay:
            repeated = self.worker.request(request)
            self.ledger["worker_batches"] += 1
            self.ledger["replay_batches"] += 1
            if canonical(results) != canonical(repeated):
                self.ledger["incidents"] += 1
                self.journal.append("incident", {"label": label, "reason": "replay_mismatch"})
                raise RuntimeError("Bit-exact replay failed")
        self.ledger["wall_seconds"] += time.perf_counter() - started
        if len(results) != len(tasks):
            raise RuntimeError("Worker omitted tasks")
        passed, records = [], []
        for task, result in zip(tasks, results):
            if result["task_id"] != task["id"]:
                raise RuntimeError("Worker changed task identity")
            self.ledger["search_expansions"] += result["cost"]["expansions"] * (2 if replay else 1)
            self.ledger["primitive_executions"] += result["cost"]["primitive_executions"] * (2 if replay else 1)
            self.ledger["model_proposal_checks"] += result["cost"].get("model_checks", 0) * (2 if replay else 1)
            expected_visible = outcomes(result["program"], task["visible"])
            authoritative_fit = expected_visible == [out for _, out in task["visible"]]
            self.ledger["oracle_string_executions"] += len(task["visible"])
            if expected_visible != result["visible_outputs"] or authoritative_fit != result["visible_fit"]:
                self.ledger["incidents"] += 1
                self.journal.append("incident", {"label": label, "task": task["id"], "reason": "execution_sensor_disagreement", "result": result})
                raise RuntimeError("Worker disagrees with independent execution sensor")
            hidden_ok = correct(result["program"], task["hidden"]) and authoritative_fit
            self.ledger["oracle_string_executions"] += len(task["hidden"])
            passed.append(int(hidden_ok))
            records.append({**result, "oracle_correct": hidden_ok})
        payload = {"label": label, "request_sha256": digest(request), "request": request, "results": records,
                   "correct": sum(passed), "n": len(tasks), "accuracy": sum(passed) / max(1, len(tasks)),
                   "visible_false_accepts": sum(row["visible_fit"] and not row["oracle_correct"] for row in records),
                   "replay_verified": replay,
                   "compute": {key: self.ledger[key] - ledger_before[key] for key in self.ledger}}
        self.journal.append("evaluation", payload)
        return payload


def paired_bootstrap(left, right, seed=20260916, resamples=2000):
    import random
    if len(left) != len(right) or not left:
        raise ValueError("Paired data required")
    deltas = [a - b for a, b in zip(left, right)]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas) for _ in range(resamples))
    return {"mean": sum(deltas) / len(deltas), "ci95": [means[int(0.025 * resamples)], means[int(0.975 * resamples)]], "unit": "paired task"}
