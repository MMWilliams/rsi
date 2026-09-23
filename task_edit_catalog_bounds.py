"""Cost-matched hindsight headroom from first-call sensor edit vocabulary."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT,write_json


OUT=ROOT/'analysis/task-edit-catalog-bounds-20260918.json'
PATHS=tuple(ROOT/f'analysis/typed-edit-effects-{run}-{stage}-20260918.json'
            for run,stages in (('meta',('admission','a','b')),
                               ('stable',('a','b')))
            for stage in stages)


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    rows=[]
    for path in PATHS:
        data=json.loads(path.read_text())
        rows.extend(data['rows'])
    assert len(rows)==1440 and len({r['id'] for r in rows})==1440
    by_bank=defaultdict(list)
    for row in rows:by_bank[row['seed']].append(row)
    assert len(by_bank)==30 and all(len(group)==48 for group in by_bank.values())
    banks=[]
    for seed,group in sorted(by_bank.items()):
        base=sum(r['outcomes']['replay_wide'] for r in group)
        top_gain=[r['outcomes']['top20_one']-r['outcomes']['replay_wide'] for r in group]
        any_gain=[max(r['outcomes']['top20_one'],r['outcomes']['minimax_one'])-
                  r['outcomes']['replay_wide'] for r in group]
        top=base+sum(sorted(top_gain,reverse=True)[:8])
        any_sensor=base+sum(sorted(any_gain,reverse=True)[:8])
        banks.append({'seed':seed,'replay_zero':base,
                      'oracle_top20_eight':top,'oracle_both_sensors_eight':any_sensor,
                      'extra_from_sensor_choice':any_sensor-top})
    result={'scope':'opened-bank hindsight, unavailable final labels',
            'tasks':len(rows),'banks':len(banks),'calls_per_bank':8,
            'totals':{name:sum(b[name] for b in banks) for name in
                      ('replay_zero','oracle_top20_eight','oracle_both_sensors_eight',
                       'extra_from_sensor_choice')},
            'top20_only_wins':sum(r['outcomes']['top20_one']>
                                   r['outcomes']['minimax_one'] for r in rows),
            'minimax_only_wins':sum(r['outcomes']['minimax_one']>
                                    r['outcomes']['top20_one'] for r in rows),
            'by_bank':banks,
            'limits':['Hindsight selects which tasks and sensor using final outcomes, unavailable at deployment.',
                      'No inference or source-acquisition cost is included.',
                      'This bounds only the tested two-sensor one-call vocabulary.']}
    write_json(OUT,result)
    print(json.dumps({k:result[k] for k in ('tasks','banks','totals',
                      'top20_only_wins','minimax_only_wins')},indent=2))


if __name__=='__main__':main()
