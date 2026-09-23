"""Audit the top-three shared-bank comparison archive."""
import argparse, json
from pathlib import Path
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.retention_run import file_hash
from run_induced_signature_v54 import bank_config

def audit(root):
    root=Path(root); read=lambda n: json.loads((root/n).read_text(encoding='utf-8'))
    sealed=read('artifact_manifest.json'); present={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert present-{'artifact_manifest.json','audit.json'}==set(sealed)
    for n,m in sealed.items(): assert file_hash(root/n)==m['sha256'] and (root/n).stat().st_size==m['bytes']
    cfg=read('config.json'); events=[json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
    assert verify_journal(root/'events.jsonl')==len(events) and events[-1]['kind']=='completed'
    for i,seed in enumerate(cfg['bank_seeds'],1):
        banks,meta=create_evolving_banks(bank_config({**cfg,'bank_seed':seed,'meta_seed':cfg['meta_seeds'][i-1]}))
        assert banks==read(f'protected_banks-{i}.json') and meta==read(f'bank_manifest-{i}.json')
    result=read('results.json'); assert result['status']=='completed'; assert events[-1]['payload']['results_sha256']==digest(result)
    report={'status':'passed','journal_events':len(events),'replications':len(cfg['bank_seeds']),'arms':3,'sealed_artifacts_checked':len(sealed),'scope':'matched top-three bounded improver pilot; no RSI claim'}
    write_json(root/'audit.json',report); return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('run'); a=ap.parse_args(); print(json.dumps(audit(ROOT/a.run),indent=2))
