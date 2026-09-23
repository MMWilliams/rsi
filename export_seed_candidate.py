"""Export an audited source candidate, explicitly pending confirmation."""
import json
from pathlib import Path
from rsi.common import ROOT,digest,write_json
from rsi.retention_run import file_hash
from seed_source_search import read,build_records
from seed_meta import extract_effects


def export():
    source=ROOT/'runs/seed-source-search-20260917'
    assert read(source/'audit.json')['status']=='passed'
    result=read(source/'results.json'); selected=result['selected']; episode=result['episodes'][selected['name']]
    records=build_records(read(source/'protected_banks.json'),read(source/'candidate_pools.json'))
    state={'status':'source candidate; evaluator transfer observed, integration incomplete; not promoted','driver':episode['driver'],'gate':selected['gate'],
        'static_tactic':episode['tactic'],'model':episode['checkpoints'][selected['checkpoint']]['model'],
        'improver_effects':extract_effects(result,records),'candidate_cap_per_source':16,'deployment_margin':.05,
        'source_selected':selected,'source_results_sha256':file_hash(source/'results.json'),
        'source_audit_sha256':file_hash(source/'audit.json')}
    confirmation=ROOT/'runs/seed-confirmation-20260917'
    if (confirmation/'audit.json').exists():
        assert read(confirmation/'audit.json')['status']=='passed'
        state['architecture_confirmation_results_sha256']=file_hash(confirmation/'results.json')
        state['architecture_confirmation_audit_sha256']=file_hash(confirmation/'audit.json')
    path=ROOT/'output/seed-improver-candidate/state.json'; write_json(path,state)
    return {'path':str(path),'sha256':digest(state),'status':state['status']}


if __name__=='__main__': print(json.dumps(export(),indent=2))
