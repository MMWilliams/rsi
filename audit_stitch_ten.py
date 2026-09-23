"""Reexecute the stitched pilot candidate generation, selection and DSL replay."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve
from stitch_ten import SEMANTIC_ARMS, mixed_banks, libraries_from_train, source_candidates, selected_score


def audit(output):
    output=Path(output); read=lambda n: json.loads((output/n).read_text(encoding="utf-8"))
    assert not (output/"FAILED.json").exists()
    sealed=read("artifact_manifest.json")
    present={p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    assert present-{"artifact_manifest.json","audit.json"}==set(sealed)
    for name,row in sealed.items():
        assert file_hash(output/name)==row["sha256"] and (output/name).stat().st_size==row["bytes"], name
    hashes=read("source_manifest.json")
    for name,value in hashes.items(): assert file_hash(output/"source"/name)==value
    cfg=read("config.json"); banks=mixed_banks(cfg)
    assert banks==read("protected_semantic_banks.json")
    libraries=libraries_from_train(banks["train"],cfg)
    assert libraries==read("libraries.json")
    events=[json.loads(line) for line in (output/"events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(output/"events.jsonl")==len(events)
    assert events[-1]["kind"]=="completed"
    closed=next(i for i,e in enumerate(events) if e["kind"]=="optimization_closed")
    assert all(i<closed for i,e in enumerate(events) if e["kind"]=="pool_split_closed")
    pools=read("candidate_pools.json"); checked=0
    for split in ("development","admission","final"):
        for task in banks[split]:
            public={"id":task["id"],"visible":task["visible"]}
            expected=[]
            for arm in SEMANTIC_ARMS:
                expected.extend(source_candidates(public,arm,libraries,cfg["candidate_cap_per_arm"]))
                checked+=1
            assert pools[task["id"]]==expected, task["id"]
    result=read("results.json")
    dev={arm:selected_score(banks["development"],pools,{arm},[arm],1)["correct"] for arm in SEMANTIC_ARMS}
    adm={arm:selected_score(banks["admission"],pools,{arm},[arm],1)["correct"] for arm in SEMANTIC_ARMS}
    priority=sorted(SEMANTIC_ARMS,key=lambda a:(-dev[a],-adm[a],a)); native=priority[0]
    routed_adm=selected_score(banks["admission"],pools,set(SEMANTIC_ARMS),priority,1)
    route=priority if routed_adm["correct"]>=adm[native] else [native]
    assert (result["development"],result["admission"],result["priority"],result["selected_priority"],result["native"])==(dev,adm,priority,route,native)
    final={arm:selected_score(banks["final"],pools,{arm},[arm],1) for arm in SEMANTIC_ARMS}
    final["stitched"]=selected_score(banks["final"],pools,set(route),route,1)
    random_priority=list(SEMANTIC_ARMS); random.Random(cfg["bank_seed"]+77).shuffle(random_priority)
    final["random_router"]=selected_score(banks["final"],pools,set(SEMANTIC_ARMS),random_priority,1)
    final["frozen_direct"]=final["v73"]
    for arm in SEMANTIC_ARMS:
        allowed=set(SEMANTIC_ARMS)-{arm}
        pr=[a for a in route if a in allowed] or [a for a in priority if a in allowed]
        final["minus_"+arm]=selected_score(banks["final"],pools,allowed,pr,1)
    assert result["semantic_final"]==final
    origins=read("dsl_prior_hashes.json"); excluded=set()
    for name,value in origins.items():
        assert file_hash(ROOT/name)==value, name
        for rows in json.loads((ROOT/name).read_text(encoding="utf-8")).values():
            excluded.update(template(t["reference"]) for t in rows if "reference" in t)
    dsl,meta=create_banks({"bank_seed":cfg["dsl_seed"],"bank_counts":{"final":cfg["dsl_tasks"]},
        "visible_examples":3,"hidden_examples":13,"max_atoms":cfg["dsl_max_atoms"]},excluded)
    assert dsl==read("protected_banks.json") and meta==read("dsl_bank_manifest.json")
    for task,archive in zip(dsl["final"],result["dsl_final"]):
        public=public_task(task)
        base=solve(public,BASE_CONFIG,cfg["dsl_budget"],cfg["dsl_max_atoms"],[],[],pool_mode="baseline")
        corrected=solve(public,BASE_CONFIG,cfg["dsl_budget"],cfg["dsl_max_atoms"],[],[],pool_mode="partial_empty")
        assert archive=={"task_id":task["id"],"baseline":base,"v8":corrected,
            "baseline_correct":correct(base["program"],task["visible"]+task["hidden"]),
            "v8_correct":correct(corrected["program"],task["visible"]+task["hidden"])}
    assert events[-1]["payload"]["sha256"]==digest(result)
    report={"status":"passed","artifacts_hashed":len(sealed),"journal_events":len(events),
        "semantic_tasks":sum(len(banks[s]) for s in ("development","admission","final")),
        "candidate_generations_replayed":checked,"dsl_searches_reexecuted":2*len(dsl["final"]),
        "scope":"two task lanes; no pooled accuracy or RSI claim"}
    write_json(output/"audit.json",report); return report

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("run"); args=ap.parse_args()
    print(json.dumps(audit(ROOT/args.run),indent=2))
