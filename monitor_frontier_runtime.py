"""Observe GPU memory outside the frozen experiment; never read final samples."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("output")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=4320)
    args = parser.parse_args()
    root = Path(args.run).resolve()
    output = Path(args.output).resolve()
    if root == output or root in output.parents:
        raise ValueError("Telemetry must remain outside the experiment archive")
    if os.name != "nt":
        raise RuntimeError("This observer uses Windows process handles")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, args.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        with output.open("x", encoding="utf-8") as stream:
            def record(kind, payload):
                stream.write(json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                         "kind": kind, "payload": payload}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            record("observer_started", {"run": str(root), "pid": args.pid, "gpu": args.gpu,
                   "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "interval_seconds": 10, "max_samples": args.max_samples,
                   "scope": "Started during initial base sampling; sampled device-wide telemetry, not allocator peaks or exclusive process attribution"})
            for _ in range(args.max_samples):
                state = kernel.WaitForSingleObject(handle, 0)
                if state != 258:
                    record("observer_stopped", {"reason": "process_exited" if state == 0 else "process_wait_error",
                           "wait_result": state, "has_failed_record": (root / "FAILED.json").exists(),
                           "has_results": (root / "results.json").exists()})
                    return
                try:
                    result = subprocess.run(["nvidia-smi", "-i", str(args.gpu),
                        "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu,temperature.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
                    record("gpu_sample", {"returncode": result.returncode, "csv": result.stdout.strip(),
                           "stderr": result.stderr.strip()})
                except (OSError, subprocess.TimeoutExpired) as exc:
                    record("observer_query_error", {"type": type(exc).__name__, "message": str(exc)})
                time.sleep(10)
            record("observer_stopped", {"reason": "sample_limit"})
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    main()
