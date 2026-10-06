"""Where does imagined discovery depart from real? Seed 644101, confident picks."""
import json, sys, warnings
import numpy as np
from rsi.common import ROOT
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import fit_restarts
from mechanism_earn_traced import load
from mechanism_self_simulation import simulate
SEED = 644101
def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    m, _ = fit_restarts(sets[:1280], K, 6, restarts=4)
    r_img, present = simulate(h, s, m, SEED, 7)
    b = json.loads((ROOT / 'analysis/mechanism-world-benchmark-20261005.json').read_text())[str(SEED)]
    bp = np.array(b[0]['present']) + np.array(b[1]['present']); bf = np.array(b[0]['found']) + np.array(b[1]['found'])
    r_true = np.where(bp >= 10, bf / np.maximum(bp, 1), np.nan)
    print('family     atoms  true-presence/world  imagined-presence/world  true r  imagined r  model r')
    for f, name in enumerate(fams):
        sel = fam == f
        ok = sel & (present >= 10) & ~np.isnan(r_true)
        print(f'{name:10s} {int(sel.sum()):5d}  {bp[sel].sum() / 1600:8.2f}  {present[sel].sum() / 800:8.2f}  '
              f'{np.nanmean(r_true[sel]) if (sel & ~np.isnan(r_true)).any() else float("nan"):6.2f}  '
              f'{r_img[ok].mean() if ok.any() else float("nan"):6.2f}  {m.r[sel & m.seen].mean() if (sel & m.seen).any() else float("nan"):6.2f}')
    ok = (present >= 10) & ~np.isnan(r_true)
    print('pearson all', round(float(np.corrcoef(r_img[ok], r_true[ok])[0, 1]), 3), 'n', int(ok.sum()))
    for f, name in enumerate(fams):
        o = ok & (fam == f)
        if o.sum() > 5: print(f'  within {name}: pearson {np.corrcoef(r_img[o], r_true[o])[0, 1]:.2f} n {int(o.sum())}')
if __name__ == '__main__':
    sys.exit(main())
