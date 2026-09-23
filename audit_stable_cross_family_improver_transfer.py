"""Independent state reconstruction and full fresh-bank replay for stable rule selection."""
from __future__ import annotations

import json
import sys

from rsi.common import ROOT,write_json
import cross_family_meta_improver_transfer as engine
import audit_cross_family_meta_improver_transfer as base_audit
from cross_family_meta_improver_development import parent_tables,train_state,fit_method
from stable_cross_family_improver_transfer import DEST,OLD,PROTOCOL,STAGES,check_source,summary


def configure():
    engine.DEST=DEST;engine.PROTOCOL=PROTOCOL;engine.STAGES=STAGES
    base_audit.DEST=DEST;base_audit.PROTOCOL=PROTOCOL;base_audit.STAGES=STAGES


def source():
    check_source()
    # Regenerate both children from the historical effects and common admission.
    engine.DEST=OLD
    tables=parent_tables();extra=engine.stage_rows('admission')
    assert len(extra)==288
    old=json.loads((OLD/'child_models.json').read_text())
    for name in ('initial','later','scrambled','duplicate'):
        assert train_state(tables[name]+extra)[0]==old[name]
    states=json.loads((DEST/'child_models.json').read_text())
    assert {k:v for k,v in states.items() if k!='later_stable'}==old
    parent=json.loads((OLD/'parent_models.json').read_text())['later']
    later_rows=tables['later']+extra
    cv=states['later']['source_cv_correct']
    assert cv['interaction_10']==cv['interaction_100']==max(cv.values())
    assert parent['selected_method']=='interaction_10'
    stable=states['later_stable']
    assert stable['selected_method']==parent['selected_method']
    assert stable['source_task_ids']==[r['id'] for r in later_rows]
    assert stable['model']==fit_method(later_rows,'interaction_10')
    assert stable['model']==states['fixed_10']['model']
    assert stable['tie_resolution']=='retain_parent_incumbent'
    result={'passed':True,'parent_states_retrained':4,'shared_admission_effects':len(extra),
            'stable_method':stable['selected_method'],'source_cv_tie':cv['interaction_10']}
    write_json(DEST/'audit_source.json',result)
    print(json.dumps(result,indent=2))


def prepare(stage):
    check_source();configure();base_audit.prepare(stage)


def score(stage):
    check_source();configure();base_audit.score(stage)


def final():
    check_source()
    names=('source','prepare_a','score_a','prepare_b','score_b')
    parts={name:json.loads((DEST/f'audit_{name}.json').read_text()) for name in names}
    assert all(x['passed'] for x in parts.values())
    reported=json.loads((DEST/'summary.json').read_text())
    assert reported==summary()
    banks=[b for stage in STAGES for b in
           json.loads((DEST/stage/'results.json').read_text())['summary']['by_bank']]
    assert reported['correct']=={name:sum(b['correct'][name] for b in banks)
                                 for name in banks[0]['correct']}
    assert reported['primary_recursive_gate']['differences']==[
        b['correct']['later_stable']-b['correct']['initial'] for b in banks]
    assert reported['secondary_correction_gate']['differences']==[
        b['correct']['later_stable']-b['correct']['later'] for b in banks]
    result={'passed':True,'parts':parts,
            'candidate_labels_rechecked':sum(parts[f'score_{s}']['candidate_labels_rechecked']
                                              for s in STAGES),
            'predicted_output_cells_rechecked':sum(parts[f'prepare_{s}']['predicted_output_cells_rechecked']
                                                   for s in STAGES)}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    actions={'source':source,'prepare_a':lambda:prepare('a'),
             'prepare_b':lambda:prepare('b'),'score_a':lambda:score('a'),
             'score_b':lambda:score('b'),'final':final}
    actions[sys.argv[1]]()
