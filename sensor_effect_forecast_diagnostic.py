"""Post-audit forecast diagnostics for frozen query-effect selectors."""
from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.metrics import average_precision_score,brier_score_loss,roc_auc_score

from rsi.common import ROOT,write_json


RUN=ROOT/'runs/listwise-budgeted-sensor-transfer-20260918'
OUT=ROOT/'analysis/sensor-effect-forecast-diagnostic-20260918.json'
NAMES=('early_logistic','early_hgb','later_logistic','later_hgb',
       'scrambled_hgb','duplicate_hgb')


def main():
    if OUT.exists():raise RuntimeError('diagnostic already exists')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    public=json.loads((RUN/'public_rows.json').read_text())
    outcome=json.loads((RUN/'results.json').read_text())['tasks']
    allocations=json.loads((RUN/'allocations.json').read_text())
    x=np.asarray([r['public_features'] for r in public],np.float32)
    y=np.asarray([r['effect']>0 for r in outcome],int)
    assert len(public)==len(outcome)==192 and int(y.sum())==12
    models={}
    for name in NAMES:
        model=joblib.load(RUN/f'{name}.joblib')
        p=model.predict_proba(x)[:,1]
        ids=set(allocations[name])
        models[name]={
            'brier':float(brier_score_loss(y,p)),
            'average_precision':float(average_precision_score(y,p)),
            'roc_auc':float(roc_auc_score(y,p)),
            'mean_predicted_positive_probability':float(p.mean()),
            'actual_positive_rate':float(y.mean()),
            'positive_effects_selected_at_96_calls':int(y[list(ids)].sum()),
            'decision_regret_to_oracle_four':12-int(y[list(ids)].sum())}
    result={'scope':'post-audit diagnostic, not predeclared promotion gate',
            'tasks':192,'positive_effects':12,'models':models}
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
