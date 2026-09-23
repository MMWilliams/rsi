"""Public candidate preparation with no oracle label computation."""
import argparse,json,time
from rsi.common import ROOT,write_json,digest
from rsi.retention_run import seal_artifacts,file_hash
from seed_v2_banks import generate
from stitch_ten import source_candidates


def prepare(output):
    output.mkdir(parents=True,exist_ok=False)
    banks=generate(); pools={}; times={'v67':0.,'v73':0.}
    hashes=[digest(t['visible']) for tasks in banks.values() for t in tasks]
    assert len(hashes)==len(set(hashes))
    write_json(output/'protected_banks.json',banks)
    write_json(output/'preparation_sources.json',{name:file_hash(ROOT/name) for name in
        ('prepare_seed_v2.py','seed_v2_banks.py','seed_casebanks.py','stitch_ten.py','rsi/evolving_domain.py')})
    for split,tasks in banks.items():
        for task in tasks:
            unique={}
            for arm in ('v67','v73'):
                start=time.perf_counter(); rows=source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16)
                times[arm]+=time.perf_counter()-start
                for row in rows: unique.setdefault(row['program'],row)
            pools[task['id']]=list(unique.values())
        print('v2 public bank prepared: '+split,flush=True)
    write_json(output/'candidate_pools.json',pools); write_json(output/'generation_times.json',times)
    seal_artifacts(output)
    return {'status':'prepared','tasks':sum(map(len,banks.values())),'oracle_labels_opened':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); args=parser.parse_args()
    print(json.dumps(prepare(ROOT/args.output),indent=2))
