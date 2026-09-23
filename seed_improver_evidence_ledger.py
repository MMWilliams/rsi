"""Create a conservative evidence ledger for the current RSI seed design."""
from __future__ import annotations

import json
from pathlib import Path

from rsi.common import ROOT, write_json


OUT = ROOT / 'analysis/seed-improver-evidence-ledger-20260918.json'
REPORT = ROOT / 'SEED-IMPROVER-EVIDENCE-LEDGER-2026-09-18.md'


def artifact(path):
    p = ROOT / path
    return {'path': path, 'exists': p.exists(),
            'audit_passed': (json.loads((p / 'audit.json').read_text())['passed']
                             if (p / 'audit.json').exists() else None)}


def main():
    if OUT.exists():
        raise RuntimeError('ledger already exists')
    rows = [
        {'name': 'dual-specialist confidence seed', 'role': 'evaluator',
         'scope': 'mixed familiar/shifted AST', 'transfer_gain': 21,
         'transfer_tasks': 192, 'source': 'familiar specialist 64 -> dual 85',
         'feedback_gain': None, 'child_gain': None, 'cost': '38,184 candidate scores',
         'decision': 'retain as lower-cost operating fallback',
         'evidence': 'runs/dual-specialist-integration-transfer-20260918'},
        {'name': 'task-level listwise top-200 objective', 'role': 'evaluator edit',
         'scope': 'mixed familiar/shifted AST', 'transfer_gain': 17,
         'transfer_tasks': 384, 'source': 'later listwise 185 vs dual top-200 168; BCE 173',
         'feedback_gain': 6, 'child_gain': None, 'cost': '225,384 candidate scores; 112,610 source labels',
         'decision': 'promote as a scoped evaluator training principle; keep high-cost',
         'evidence': 'runs/task-listwise-top200-replication-20260918'},
        {'name': 'candidate-level stacked ranker', 'role': 'evaluator edit',
         'scope': 'mixed familiar/shifted AST', 'transfer_gain': 4,
         'transfer_tasks': 192, 'source': 'later stack 68 vs dual 64',
         'feedback_gain': 2, 'child_gain': None, 'cost': '57,600 top-100 candidate scores',
         'decision': 'retain in shadow catalog; no promotion gate',
         'evidence': 'runs/candidate-stacking-feedback-transfer-20260918'},
        {'name': 'shortlist width-200 edit', 'role': 'search edit',
         'scope': 'mixed familiar/shifted AST', 'transfer_gain': 3,
         'transfer_tasks': 192, 'source': 'dual top-100 74 -> selective/all width 77',
         'feedback_gain': 0, 'child_gain': None, 'cost': 'about 2x specialist candidate scoring',
         'decision': 'retain as optional costed action; no learned controller',
         'evidence': 'runs/selective-width-feedback-transfer-20260918'},
        {'name': 'one exact output sensor', 'role': 'evaluator action',
         'scope': 'mixed familiar/shifted AST', 'transfer_gain': 8,
         'transfer_tasks': 192, 'source': 'listwise no-query 91 -> all-query 103; learned 99',
         'feedback_gain': 2, 'child_gain': None, 'cost': '96 calls for selective arm; 192 all-query',
         'decision': 'retain action; do not promote learned allocator',
         'evidence': 'runs/listwise-budgeted-sensor-transfer-20260918'},
        {'name': 'bounded cross-family effect-table improver', 'role': 'improver',
         'scope': 'mixed transition families', 'transfer_gain': None,
         'transfer_tasks': 576, 'source': 'admission +10; transfer later child 340',
         'feedback_gain': None, 'child_gain': -2, 'cost': '96 logical calls/policy; 288 admission probes',
         'decision': 'reject as seed improver; use as negative control',
         'evidence': 'runs/cross-family-meta-improver-transfer-20260918'},
    ]
    for row in rows:
        row['audit'] = artifact(row['evidence'])
    rubric = {
        'evaluator_quality': 'held-out oracle choice gain with reachability reported',
        'improver_quality': 'later parent child gain against initial/scrambled/duplicate/fixed',
        'integration_quality': 'same-base, matched source and deployment costs',
        'recursive_requirement': 'child improver must improve a second untouched base',
        'oracle_boundary': 'external interpreter and hidden banks remain outside edits',
    }
    ranking = [
        {'rank': 1, 'candidate': 'listwise objective + dual-specialist fallback',
         'why': 'only evaluator edit with independent replicated objective gate; dual route supplies lower-cost fallback',
         'status': 'best current evaluator seed, not recursive improver'},
        {'rank': 2, 'candidate': 'listwise evaluator + exact output sensor action',
         'why': 'sensor closes useful reachability gaps, but learned allocation failed and one run had timing deviation',
         'status': 'shadow integrated system'},
        {'rank': 3, 'candidate': 'dual-specialist + stacked ranker + width',
         'why': 'complementary solver gains, but combined integration gates and improver growth remain unproved',
         'status': 'research catalog'},
        {'rank': 4, 'candidate': 'bounded effect-table improver',
         'why': 'admission gain did not transmit to a stronger child; later child lost to initial and fixed controls',
         'status': 'negative control'},
    ]
    result = {'date': '2026-09-18', 'rows': rows, 'rubric': rubric,
              'ranking': ranking,
              'conclusion': 'No positive recursive feedback loop is demonstrated. The most defensible seed is a cost-aware listwise evaluator with dual-specialist fallback and exact sensor actions, wrapped in a descendant-aware improver test.',
              'next_gate': 'later child must beat initial, scrambled, duplicate and strongest fixed parent on an untouched mechanism set using output-blind preparation and matched resource vectors'}
    write_json(OUT, result)
    lines = ['# Seed improver evidence ledger', '',
             'This ledger keeps evaluator gain, action value and recursive improver gain separate. A score increase does not count as improver intelligence unless the later parent creates a stronger child improver on a new base.', '']
    lines += ['| Rank | Candidate | Evidence | Decision |', '| --- | --- | --- | --- |']
    for item in ranking:
        lines.append(f"| {item['rank']} | {item['candidate']} | {item['why']} | {item['status']} |")
    lines += ['', '## Component ledger', '', '| Component | Role | Held-out evidence | Feedback / child | Cost | Decision |', '| --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| {row['name']} | {row['role']} | {row['source']} | {row['feedback_gain']} / {row['child_gain']} | {row['cost']} | {row['decision']} |")
    lines += ['', '## Current conclusion', '', result['conclusion'], '', 'The next parent/child gate is: ' + result['next_gate'] + '.', '', 'The external oracle, hidden examples and sealed test-bank generator remain outside the edit loop.']
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'report': str(REPORT),
                      'conclusion': result['conclusion']}, indent=2))


if __name__ == '__main__':
    main()
