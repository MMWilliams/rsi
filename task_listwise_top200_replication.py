"""Independent 48-bank replication with the frozen top-200 evaluator models."""
from __future__ import annotations

import sys

from rsi.common import ROOT
import task_listwise_top200_transfer as base


base.DEST = ROOT/'runs/task-listwise-top200-replication-20260918'
base.PROTOCOL = ROOT/'EXPERIMENT-task-listwise-top200-replication.md'
base.SCRIPT = ROOT/'task_listwise_top200_replication.py'
base.SEEDS = tuple(range(905500,905548))

original_manifest=base.manifest
original_summarize=base.summarize


def manifest():
    value=original_manifest()
    value['tasks']=len(base.SEEDS)*8
    return value


def summarize(outcome,rows,checked):
    result=original_summarize(outcome,rows,checked)
    c=result['comparisons']
    t=result['totals']
    obj=c['later_listwise_minus_later_bce']
    early=c['later_listwise_minus_early_listwise']
    dual=c['later_listwise_minus_dual200']
    prior=c['later_listwise_minus_prior_stack']
    feedback=(all(c[f'later_listwise_minus_{name}']['gain']>=8 for name in
                  ('early_listwise','scrambled_listwise','duplicate_listwise'))
              and early['interval'][0]>0 and early['positive_banks']>=8)
    objective=(obj['gain']>=12 and obj['interval'][0]>0 and
               obj['positive_banks']>=12)
    integration=(dual['gain']>=16 and prior['gain']>=16 and
                 dual['interval'][0]>0 and prior['interval'][0]>0 and
                 dual['positive_banks']>=16 and
                 t['later_listwise_familiar']>=t['familiar200_familiar']-8 and
                 t['later_listwise_shifted']>=t['shifted200_shifted']-8)
    result['gates']={'objective_replication':objective,
                     'incremental_checkpoint':feedback,
                     'integration_replication':integration}
    result['scope']='independent 48-bank replication; original 24-bank gates remain failed'
    return result


base.manifest=manifest
base.summarize=summarize


if __name__=='__main__':
    {'prepare':base.prepare,'score':base.score,'audit':base.audit}[sys.argv[1]]()
