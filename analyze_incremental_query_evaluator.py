"""Score forecast quality and query regret for opened-bank evaluator checkpoints."""
import json

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_development import values
from cross_family_meta_improver_transfer import stage_rows

SOURCE=ROOT/'analysis/incremental-query-evaluator-development-20260918.json'
OUT=ROOT/'analysis/incremental-query-evaluator-diagnostics-20260918.json'


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    data=json.loads(SOURCE.read_text())
    rows=stage_rows('a')+stage_rows('b')
    y=np.asarray([r['gain'] for r in rows],float)
    seeds=sorted({r['seed'] for r in rows})
    models=data['models']
    metrics={}
    for name,model in models.items():
        pred=values(model,rows)
        metrics[name]={'forecast_mse':float(np.mean((pred-y)**2)),
                       'forecast_mae':float(np.mean(np.abs(pred-y))),
                       'forecast_bias':float(np.mean(pred-y)),
                       'selected_true_gain':sum(
                           sum(r['gain'] for r in rows if r['seed']==seed and
                               r['id'] in set(next(b['chosen'][name] for b in data['banks']
                                                   if b['seed']==seed))) for seed in seeds),
                       'oracle_best_eight_gain':sum(sum(sorted(
                           (r['gain'] for r in rows if r['seed']==seed),reverse=True)[:8])
                                                    for seed in seeds)}
    choices={b['seed']:{name:set(ids) for name,ids in b['chosen'].items()}
             for b in data['banks']}
    overlap={'e0_e3':sum(len(c['e0']&c['e3']) for c in choices.values()),
             'e0_e6':sum(len(c['e0']&c['e6']) for c in choices.values()),
             'e6_scrambled':sum(len(c['e6']&c['scrambled_e6']) for c in choices.values())}
    result={'scope':'opened-bank developmental diagnostics','tasks':len(rows),
            'calls_per_checkpoint':len(seeds)*8,'metrics':metrics,
            'selected_call_overlap':overlap,'source_sha256':data['source_sha256']}
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
