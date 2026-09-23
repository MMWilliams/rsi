"""Re-screen the complexity-partition environment against a capacity-matched
zero-knowledge default.

`complexity_partition_environment.py` reported default regret of +123, +101 and
+89 and a P2d pass, making this the first action space to clear all four
preconditions. Its adversarial defaults were the most-confident rule, a 15-leaf
pooled model and the best constant. The capacity-matched audit on the
construction runs then showed a single 60-leaf pooled model beats every 15-leaf
built system by 36 to 50 and beats 60-leaf specialists too.

So the question is whether the partition's apparent structure survives an
adversarial default that includes model capacity. On the same source and target
panels as the original screen:

  pooled15         the original pooled default
  pooled60         one 60-leaf model, same source labels
  pooled120        one 120-leaf model, same source labels
  most_confident   over the four original 15-leaf specialists
  own_bin_latent   the original latent upper reference over 15-leaf specialists
  oracle15         per-task max over the original five actions
  oracle_all       per-task max over the original five plus pooled60/120

P2c is recomputed as oracle minus the best of every zero-knowledge arm, with
pooled60 and pooled120 now in that set. P2d is recomputed as a held-out selector
over all scored actions against that best default. Development on opened
panels; nothing frozen.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import SOURCE, TARGET, load_cache
import complexity_partition_environment as env


OUT = ROOT / 'analysis/partition-rescreen-capacity-20260921.json'
ORIGINAL = ROOT / 'analysis/complexity-partition-models-20260920'
THRESHOLD = 20


def big(leaves):
    return HistGradientBoostingClassifier(
        max_leaf_nodes=leaves, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def main():
    if OUT.exists():
        raise RuntimeError('rescreen exists')
    px, py = env.rows_for(env.SOURCE)
    models = {n: joblib.load(ORIGINAL / f'{n}.joblib')
              for n in ('shallow', 'mid', 'deep', 'pooled')}
    models['pooled60'] = big(60).fit(px, py)
    models['pooled120'] = big(120).fit(px, py)
    original = ['shallow', 'mid', 'deep', 'pooled']
    all_actions = original + ['pooled60', 'pooled120', 'e0']
    panels = {n: env.evaluate(n, models) for n in TARGET}

    result = {'scope': 'opened development; partition environment re-screened '
                       'with capacity-matched pooled defaults',
              'threshold': THRESHOLD, 'panels': {}}
    for name, rows in panels.items():
        arms = {
            'pooled15': env.totals(rows, ['pooled'] * len(rows)),
            'pooled60': env.totals(rows, ['pooled60'] * len(rows)),
            'pooled120': env.totals(rows, ['pooled120'] * len(rows)),
            'most_confident15': env.totals(rows, [
                max(original, key=lambda a: (r['confidence'][a], a)) for r in rows]),
            'own_bin_latent15': env.totals(rows, [
                r['bin'] if r['bin'] in original[:3] else 'pooled' for r in rows]),
            'oracle15': env.totals(rows, [
                max(original + ['e0'], key=lambda a: r['labels'][a]) for r in rows]),
            'oracle_all': env.totals(rows, [
                max(all_actions, key=lambda a: r['labels'][a]) for r in rows]),
        }
        free = {k: v for k, v in arms.items()
                if k in ('pooled15', 'pooled60', 'pooled120', 'most_confident15')}
        best_free = max(free, key=lambda k: sum(free[k]))
        regret_vs_all = sum(arms['oracle_all']) - sum(free[best_free])
        regret_vs_15 = sum(arms['oracle15']) - sum(free[best_free])
        latent_minus_best = env.compare(arms['own_bin_latent15'], free[best_free])
        result['panels'][name] = {
            'totals': {k: sum(v) for k, v in arms.items()},
            'best_free_default': best_free,
            'default_regret_vs_oracle_all': regret_vs_all,
            'default_regret_vs_oracle15': regret_vs_15,
            'p2c_passed': bool(regret_vs_all > THRESHOLD),
            'own_bin_latent_minus_best_default': latent_minus_best}
        v = result['panels'][name]
        print('{:32s} '.format(name[:32]) + ' '.join(
            '{}={}'.format(k, sum(arms[k])) for k in arms), flush=True)
        print('   best free={} regret(vs oracle_all)={:+d} regret(vs oracle15)={:+d} '
              'P2c={}  latent-best={:+d} {}'.format(
                  best_free, regret_vs_all, regret_vs_15, v['p2c_passed'],
                  latent_minus_best['gain'], latent_minus_best['interval']), flush=True)

    # P2d: selector over all scored actions, fitted on two panels, tested on third
    tn = list(TARGET)
    train = [r for n in tn[:2] for r in panels[n]]
    test = panels[tn[2]]
    scored = sorted(models)
    xtr = np.asarray([env.feats(r, scored) for r in train], np.float32)
    sel = {}
    for a in all_actions:
        y = np.asarray([r['labels'][a] for r in train], np.int8)
        sel[a] = model_for(15).fit(xtr, y) if 0 < y.sum() < len(y) else float(y.mean())
    xte = np.asarray([env.feats(r, scored) for r in test], np.float32)
    pred = {a: (np.full(len(test), m) if isinstance(m, float)
                else m.predict_proba(xte)[:, 1]) for a, m in sel.items()}
    learned = env.totals(test, [max(all_actions, key=lambda a: (float(pred[a][i]), a))
                                for i in range(len(test))])
    bf = result['panels'][tn[2]]['best_free_default']
    default = env.totals(test, [{'pooled15': 'pooled', 'pooled60': 'pooled60',
                                 'pooled120': 'pooled120'}.get(bf, 'pooled60')] * len(test)) \
        if bf != 'most_confident15' else env.totals(test, [
            max(original, key=lambda a: (r['confidence'][a], a)) for r in test])
    against = env.compare(learned, default)
    result['learnability'] = {'train': tn[:2], 'test': tn[2], 'learned': sum(learned),
                              'default_used': bf, 'default': sum(default),
                              'learned_minus_default': against,
                              'p2d_passed': bool(against['gain'] > 0 and against['interval'][0] > 0)}
    print('P2d: learned={} vs {}={} -> {:+d} {}w/{}l {} passed={}'.format(
        sum(learned), bf, sum(default), against['gain'], against['positive_banks'],
        against['losing_banks'], against['interval'], result['learnability']['p2d_passed']))
    result['verdict'] = {'p2c_all_panels': all(v['p2c_passed'] for v in result['panels'].values()),
                         'p2d': result['learnability']['p2d_passed']}
    result['limits'] = ['Opened panels; development only.',
                        'pooled60/120 are trained on the same source labels as the original '
                        'specialists, so label exposure is matched.',
                        'Leaf count is one capacity axis.']
    write_json(OUT, result)
    print('verdict:', result['verdict'])


if __name__ == '__main__':
    main()
