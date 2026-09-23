"""Run a frozen second candidate-reranker panel without changing source models."""
from __future__ import annotations

import json
import shutil
import sys

from rsi.common import ROOT,write_json
import candidate_reranker_transfer as transfer
from cross_family_meta_improver_transfer import interval


DEST=ROOT/'runs/candidate-reranker-replication-20260918'
PROTOCOL=ROOT/'EXPERIMENT-candidate-reranker-replication.md'
SOURCE=ROOT/'runs/candidate-reranker-transfer-20260918'
SEEDS=tuple(range(902522,902534))


def configure():
    transfer.DEST=DEST
    transfer.PROTOCOL=PROTOCOL
    transfer.SEEDS=SEEDS


def prepare():
    if DEST.exists():raise RuntimeError('replication run already exists')
    assert json.loads((SOURCE/'audit.json').read_text())['passed']
    source=json.loads((SOURCE/'source_manifest.json').read_text())
    DEST.mkdir(parents=True)
    for name in source['model_sha256']:
        shutil.copy2(SOURCE/f'{name}.joblib',DEST/f'{name}.joblib')
        assert transfer.sha(DEST/f'{name}.joblib')==source['model_sha256'][name]
    source['protocol_sha256']=transfer.sha(PROTOCOL)
    source['replicated_from']=str(SOURCE.relative_to(ROOT))
    write_json(DEST/'source_manifest.json',source)
    configure()
    transfer.freeze_banks()


def score():
    configure()
    transfer.score_banks()


def audit():
    configure()
    import audit_candidate_reranker_transfer as independent
    independent.main()


def report():
    assert json.loads((DEST/'audit.json').read_text())['passed']
    fresh=json.loads((DEST/'results.json').read_text())
    prior=json.loads((SOURCE/'results.json').read_text())
    rows=fresh['tasks'];by_seed={seed:[] for seed in SEEDS}
    for row in rows:by_seed[row['seed']].append(row)
    fallback={}
    for mode in ('zero','budget_eight'):
        diffs=[];e1_total=0;fallback_total=0
        allocation=json.loads((DEST/'frozen_allocations.json').read_text())
        for seed in SEEDS:
            selected=set(allocation[str(seed)]) if mode=='budget_eight' else set()
            e1=0;routed=0
            for row in by_seed[seed]:
                endpoint=row['one'] if row['id'] in selected else row['zero']
                e1+=endpoint['e1']
                chosen='old' if row['family']=='self_edit_transition' else 'e1'
                routed+=endpoint[chosen]
            e1_total+=e1;fallback_total+=routed;diffs.append(routed-e1)
        fallback[mode]={'e1':e1_total,'fallback':fallback_total,'difference':sum(diffs),
                        'by_bank':diffs,'interval':interval(diffs)}
    primary=fresh['summary']['gate']
    fallback['supported']=(fallback['zero']['difference']>0 and
        fallback['zero']['interval'][0]>0 and
        fallback['budget_eight']['difference']>=0)
    prior_diffs=prior['summary']['e1_minus_e0_by_bank']
    pooled=prior_diffs+fresh['summary']['e1_minus_e0_by_bank']
    summary={'primary_new_panel':primary,'pooled_descriptive':{
        'e1_minus_e0':sum(pooled),'positive_banks':sum(v>0 for v in pooled),
        'losing_banks':sum(v<0 for v in pooled),'interval':interval(pooled)},
        'self_edit_fallback':fallback,
        'fresh_totals':fresh['summary']['totals'],
        'fresh_resource_counts':json.loads((DEST/'bank_manifest.json').read_text()),
        'limits':['Same synthetic generator as original panel.',
                  'Source labels and models are unchanged; no child improver was trained.',
                  'Pooled analysis includes the opened first panel and is descriptive.']}
    if (DEST/'replication_report.json').exists():raise RuntimeError('report exists')
    write_json(DEST/'replication_report.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit,'report':report}[sys.argv[1]]()
