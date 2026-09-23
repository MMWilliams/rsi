"""Check output-blind preparation against eight archived audited tasks."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT,write_json
from public_ast_probe_prepare import prepare_public


RUN=ROOT/'runs/listwise-budgeted-sensor-transfer-20260918'
OUT=ROOT/'analysis/public-ast-probe-preparer-equivalence-20260918.json'
SCRIPT=ROOT/'public_ast_probe_prepare.py'


def main():
    if OUT.exists():raise RuntimeError('equivalence artifact already exists')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    tasks=json.loads((RUN/'sealed_bank.json').read_text())[:8]
    expected={name:json.loads((RUN/name).read_text()) for name in
              ('base_pools.json','ast_wide_pools.json',
               'predicted_probe_outputs.json','frozen_records.json')}
    base,wide,matrix,records,cost=prepare_public(tasks)
    for task,rec in zip(tasks,records):
        key=task['id']
        assert base[key]==expected['base_pools.json'][key]
        assert wide[key]==expected['ast_wide_pools.json'][key]
        assert matrix[key]==expected['predicted_probe_outputs.json'][key]
        old=next(r for r in expected['frozen_records.json'] if r['id']==key)
        for field in ('id','seed','pool_sha256','old_scores','probe'):
            assert rec[field]==old[field],(key,field)
        assert rec['orders']['old']==old['orders']['old']
        assert 'probe_output' not in rec
    result={'passed':True,'archived_tasks_checked':len(tasks),
            'base_candidates_checked':cost['base_candidates'],
            'wide_candidates_checked':sum(map(len,wide.values())),
            'predicted_output_cells_checked':cost['predicted_output_cells'],
            'old_ranker_orders_and_probes_checked':len(records),
            'preparer_sha256':hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
            'archived_audit_sha256':hashlib.sha256(
                (RUN/'audit.json').read_bytes()).hexdigest(),
            'true_output_field_created':False}
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
