"""Post-audit evaluation of frozen width-edit probability forecasts."""
from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss

from rsi.common import ROOT, write_json
from selective_width_feedback_transfer import DEST, sha


def main():
    assert json.loads((DEST / 'audit.json').read_text())['passed']
    out = ROOT / 'analysis/selective-width-forecast-diagnostics-20260918.json'
    if out.exists():
        raise RuntimeError('diagnostics already exist')
    rows = json.loads((DEST / 'public_rows.json').read_text())
    outcome = json.loads((DEST / 'results.json').read_text())['tasks']
    x = np.asarray([r['public_features'] for r in rows], np.float32)
    y100 = np.asarray([r['outcomes']['100'] for r in outcome], float)
    y200 = np.asarray([r['outcomes']['200'] for r in outcome], float)
    effect = y200 - y100
    diagnostic = {}
    for name in ('early', 'later', 'scrambled', 'duplicate'):
        heads = joblib.load(DEST / f'{name}.joblib')
        p100 = heads['100'].predict_proba(x)[:, 1]
        p200 = heads['200'].predict_proba(x)[:, 1]
        forecast = p200 - p100
        diagnostic[name] = {
            'brier_100': float(brier_score_loss(y100, p100)),
            'brier_200': float(brier_score_loss(y200, p200)),
            'effect_mse': float(np.mean((forecast - effect) ** 2)),
            'effect_mae': float(np.mean(abs(forecast - effect))),
            'effect_bias': float(np.mean(forecast - effect)),
            'positive_edit_average_precision': float(
                average_precision_score(effect > 0, forecast)),
            'mean_predicted_effect': float(np.mean(forecast)),
            'positive_edits_in_top_96': int(sum(effect[
                np.argsort(-forecast)[:96]] > 0)),
        }
    result = {'scope': 'post-audit diagnostic on frozen models and target; '
                       'not a new promotion gate',
              'manifest_sha256': sha(DEST / 'manifest.json'),
              'audit_sha256': sha(DEST / 'audit.json'),
              'tasks': len(rows), 'positive_effects': int(sum(effect > 0)),
              'negative_effects': int(sum(effect < 0)),
              'actual_mean_effect': float(np.mean(effect)),
              'models': diagnostic}
    write_json(out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
