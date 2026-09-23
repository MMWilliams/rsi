import numpy as np, json
from rsi.common import ROOT, write_json
from region_specialist_repayment_development import TARGET
import construction_improver_development as dev
import recursive_improver_development as rec

panels = dev.load_banks()
tname = TARGET[2]
transfer = panels[tname]
pool = [b for n, bs in panels.items() if n != tname for b in bs]

print('scheme default-regret screen: does the CHOICE matter at each child size?')
print('{:6s} '.format('size') + ' '.join('{:>8s}'.format(s) for s in rec.SCHEMES)
      + '   oracle default regret')
out = {}
for size in (3, 6, 12, 24):
    hist = pool[:size]
    scores = {}
    for name, edges in rec.SCHEMES.items():
        scores[name] = sum(rec.score_on(transfer, hist, edges))
    oracle = max(scores.values())
    default = scores[rec.DEFAULT_SCHEME]
    out[str(size)] = {'scores': scores, 'oracle': oracle,
                      'default': default, 'regret': oracle - default}
    print('{:6d} '.format(size) + ' '.join('{:8d}'.format(scores[s]) for s in rec.SCHEMES)
          + '   {:6d} {:7d} {:+6d}'.format(oracle, default, oracle - default))
write_json(ROOT / 'analysis/scheme-choice-regret-20260921.json',
           {'scope': 'precondition screen for the recursive action space',
            'transfer_panel': tname, 'by_child_history_size': out,
            'limits': ['Opened panels; development only.',
                       'Regret here uses the transfer panel, so it is an upper '
                       'bound on what any parent could transmit.']})
