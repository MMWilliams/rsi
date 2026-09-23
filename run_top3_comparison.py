"""Matched fresh-bank comparison of the three recommended bounded improvers."""
from __future__ import annotations
import argparse, json, shutil, time
from pathlib import Path
from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.retention_run import file_hash, seal_artifacts
from run_induced_signature_v54 import bank_config
import run_meta_ast_v67 as v67
import run_mutation_stack_v72 as v72
import run_self_editing_grammar_v73 as v73

def run(config, root):
    root = Path(root); root.mkdir(parents=True, exist_ok=False); journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    source_names = ["run_top3_comparison.py", config["protocol"], "run_meta_ast_v67.py", "run_mutation_stack_v72.py", "run_self_editing_grammar_v73.py",
                    "run_ast_v66.py", "run_induced_signature_v54.py", "rsi/evolving_domain.py", "rsi/meta_ast.py", "rsi/meta_mutation.py", "rsi/meta_self_edit.py",
                    "rsi/ast_synthesis.py", "rsi/mutation_synthesis.py", "rsi/self_editing_grammar.py", "rsi/stack_program.py", "rsi/expression_synthesis.py",
                    "rsi/semantic_invention.py", "rsi/common.py", "rsi/retention_run.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = root / "source" / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / name, dest)
    write_json(root / "config.json", config); journal.append("preregistration", {"config": config, "source_sha256": hashes})
    all_results = {}
    for index, (bank_seed, meta_seed) in enumerate(zip(config["bank_seeds"], config["meta_seeds"]), 1):
        cfg = {**config, "bank_seed": bank_seed, "meta_seed": meta_seed}
        banks, metadata = create_evolving_banks(bank_config(cfg))
        write_json(root / f"protected_banks-{index}.json", banks); write_json(root / f"bank_manifest-{index}.json", metadata)
        journal.append("banks_frozen", {"replication": index, "sha256": digest(banks), "metadata": metadata})
        arms = {}
        for name, mod in (("v67", v67), ("v72", v72), ("v73", v73)):
            t0 = time.perf_counter(); pools = mod.build_pools(banks)
            if name == "v67":
                frozen = {"weights": [100,10,5,2,1,0,-1]}; pop = mod.initial_population(meta_seed, size=config["population_size"])
                evolved, trace = mod.evolve(pop, pools["development"], {t["id"]: t for t in banks["development"]}, generations=config["generations"], elite_count=config["elite_count"], seed=meta_seed)
                scores = {"frozen": mod.score_pools(pools, banks, frozen, "frozen"), "evolved": mod.score_pools(pools, banks, evolved, "evolved")}
                eligible = ["frozen"] + (["evolved"] if scores["evolved"]["admission"]["correct"] >= scores["frozen"]["admission"]["correct"] else [])
                selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm)); arch = evolved
            elif name == "v72":
                frozen = {"max_terms": 0, "rank_mode": "shortest"}; broad = {"max_terms": 8, "rank_mode": "shortest"}; pop = mod.initial_population(meta_seed, size=config["population_size"])
                evolved, trace = mod.evolve(pop, pools["development"], generations=config["generations"], elite_count=config["elite_count"], seed=meta_seed)
                scores = {"frozen": mod.score_arm(pools, banks, frozen, "frozen"), "broad": mod.score_arm(pools, banks, broad, "broad"), "evolved": mod.score_arm(pools, banks, evolved, "evolved")}
                eligible = ["broad"] + (["evolved"] if scores["evolved"]["admission"]["correct"] >= scores["broad"]["admission"]["correct"] else [])
                selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm)); arch = evolved
            else:
                frozen = {"enabled_ops": [], "max_complexity": 999, "rank_mode": "shortest"}; broad = {"enabled_ops": list(mod.SAFE_OPS), "max_complexity": 999, "rank_mode": "shortest"}; pop = mod.initial_population(meta_seed, size=config["population_size"])
                evolved, trace = mod.evolve(pop, pools["development"], generations=config["generations"], elite_count=config["elite_count"], seed=meta_seed)
                scores = {"frozen": mod.score_arm(pools, banks, frozen, "frozen"), "broad": mod.score_arm(pools, banks, broad, "broad"), "evolved": mod.score_arm(pools, banks, evolved, "evolved")}
                eligible = ["broad"] + (["evolved"] if scores["evolved"]["admission"]["correct"] >= scores["broad"]["admission"]["correct"] else [])
                selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm)); arch = evolved
            arms[name] = {"scores": scores, "eligible": eligible, "selected": selected, "architecture": arch, "trace": trace, "pool_wall_seconds": time.perf_counter() - t0}
            journal.append("arm_completed", {"replication": index, "arm": name, "selected": selected, "scores_sha256": digest(scores)})
        all_results[str(index)] = arms
    result = {"status": "completed", "replications": all_results, "elapsed_seconds": time.perf_counter() - started, "scope": "matched top-three bounded improver comparison; no RSI claim"}
    write_json(root / "results.json", result)
    if any(file_hash(ROOT / n) != h for n,h in hashes.items()): raise RuntimeError("source changed during comparison")
    journal.append("completed", {"results_sha256": digest(result)}); seal_artifacts(root); return result

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("output"); ap.add_argument("--config", default="configs/top3-comparison.json"); a=ap.parse_args()
    print(json.dumps(run(json.loads((ROOT/a.config).read_text()), ROOT/a.output), indent=2))
