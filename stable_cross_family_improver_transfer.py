"""Prospective transfer of an incumbent-aware bounded evaluator-rule improver."""
from __future__ import annotations

import json
import sys
from copy import deepcopy

from rsi.common import ROOT,write_json
import cross_family_meta_improver_transfer as engine
from cross_family_query_value_development import CONTROLS

OLD=ROOT/'runs/cross-family-meta-improver-transfer-20260918'
DEST=ROOT/'runs/stable-cross-family-improver-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-stable-cross-family-improver-transfer.md'
STAGES={'a':tuple(range(902438,902444)),
        'b':tuple(range(902444,902450))}


def configure():
    engine.DEST=DEST
    engine.PROTOCOL=PROTOCOL
    engine.STAGES=STAGES


def source():
    if DEST.exists():raise RuntimeError('run already exists')
    old=json.loads((OLD/'child_models.json').read_text())
    parents=json.loads((OLD/'parent_models.json').read_text())
    gate=json.loads((OLD/'admission_gate.json').read_text())
    assert gate['admit']
    assert parents['later']['selected_method']=='interaction_10'
    assert old['initial']['selected_method']=='interaction_10'
    assert old['later']['selected_method']=='interaction_100'
    cv=old['later']['source_cv_correct']
    assert cv['interaction_10']==cv['interaction_100']==max(cv.values())
    assert old['fixed_10']['source_task_ids']==old['later']['source_task_ids']
    states=deepcopy(old)
    stable=deepcopy(old['later'])
    stable['selected_method']='interaction_10'
    stable['model']=deepcopy(old['fixed_10']['model'])
    stable['tie_resolution']='retain_parent_incumbent'
    states['later_stable']=stable
    write_json(DEST/'child_models.json',states)
    write_json(DEST/'admission_gate.json',gate)
    manifest={'protocol_sha256':engine.sha(PROTOCOL),
              'wrapper_sha256':engine.sha(ROOT/'stable_cross_family_improver_transfer.py'),
              'engine_sha256':engine.sha(ROOT/'cross_family_meta_improver_transfer.py'),
              'prior_children_sha256':engine.sha(OLD/'child_models.json'),
              'prior_parents_sha256':engine.sha(OLD/'parent_models.json'),
              'prior_admission_sha256':engine.sha(OLD/'admission/results.json'),
              'prior_gate_sha256':engine.sha(OLD/'admission_gate.json'),
              'new_children_sha256':engine.sha(DEST/'child_models.json'),
              'new_gate_sha256':engine.sha(DEST/'admission_gate.json'),
              'source_tasks':{'initial':864,'later':1152},
              'selected_methods':{name:states[name]['selected_method']
                                  for name in ('initial','later','later_stable','scrambled','duplicate')}}
    write_json(DEST/'source_manifest.json',manifest)
    return manifest


def check_source():
    m=json.loads((DEST/'source_manifest.json').read_text())
    assert m['protocol_sha256']==engine.sha(PROTOCOL)
    assert m['wrapper_sha256']==engine.sha(ROOT/'stable_cross_family_improver_transfer.py')
    assert m['engine_sha256']==engine.sha(ROOT/'cross_family_meta_improver_transfer.py')
    assert m['prior_children_sha256']==engine.sha(OLD/'child_models.json')
    assert m['prior_parents_sha256']==engine.sha(OLD/'parent_models.json')
    assert m['prior_admission_sha256']==engine.sha(OLD/'admission/results.json')
    assert m['prior_gate_sha256']==engine.sha(OLD/'admission_gate.json')
    assert m['new_children_sha256']==engine.sha(DEST/'child_models.json')
    assert m['new_gate_sha256']==engine.sha(DEST/'admission_gate.json')


def prepare(stage):
    check_source();configure()
    return engine.prepare_stage(stage)


def score(stage):
    check_source();configure()
    assert all((DEST/s/'manifest.json').exists() for s in STAGES)
    return engine.score_stage(stage)


def summary():
    panels={s:json.loads((DEST/s/'results.json').read_text())['summary'] for s in STAGES}
    banks=[b for s in STAGES for b in panels[s]['by_bank']]
    correct={name:sum(b['correct'][name] for b in banks) for name in banks[0]['correct']}
    recursive=[b['correct']['later_stable']-b['correct']['initial'] for b in banks]
    correction=[b['correct']['later_stable']-b['correct']['later'] for b in banks]
    ci=engine.interval(recursive);corr_ci=engine.interval(correction)
    fixed_best=max(CONTROLS,key=lambda name:correct[name])
    gate=json.loads((DEST/'admission_gate.json').read_text())
    primary=(gate['admit'] and sum(d>0 for d in recursive)>=8 and ci[0]>0
             and correct['later_stable']>correct['parent_later']
             and correct['later_stable']>correct['later']
             and correct['later_stable']>correct['scrambled']
             and correct['later_stable']>correct['duplicate']
             and correct['later_stable']>correct[fixed_best]
             and correct['later_stable']>=max(correct['fixed_10'],correct['fixed_100']))
    return {'scope':'incumbent-aware bounded evaluator-rule improver transfer',
            'tasks':sum(p['tasks'] for p in panels.values()),
            'reachable':sum(p['reachable'] for p in panels.values()),
            'no_query':sum(p['no_query'] for p in panels.values()),
            'logical_calls_per_policy':96,
            'correct':correct,
            'by_panel':{s:p['correct'] for s,p in panels.items()},
            'by_bank':banks,
            'primary_recursive_gate':{'differences':recursive,'positive_banks':sum(d>0 for d in recursive),
                                      'bank_bootstrap_95_sum':ci,'strongest_fixed':fixed_best,
                                      'passed':primary},
            'secondary_correction_gate':{'differences':correction,
                                         'positive_banks':sum(d>0 for d in correction),
                                         'bank_bootstrap_95_sum':corr_ci,
                                         'passed':correct['later_stable']>correct['later'] and corr_ci[0]>0},
            'historical_source_tasks':{'initial':576,'later':864},
            'shared_prior_admission_tasks':288,
            'new_transfer_oracle_calls_per_policy':96}


def final():
    check_source();result=summary();write_json(DEST/'summary.json',result)
    return {'correct':result['correct'],
            'primary_recursive_gate':result['primary_recursive_gate'],
            'secondary_correction_gate':result['secondary_correction_gate']}


if __name__=='__main__':
    actions={'source':source,'prepare_a':lambda:prepare('a'),
             'prepare_b':lambda:prepare('b'),'score_a':lambda:score('a'),
             'score_b':lambda:score('b'),'final':final}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
