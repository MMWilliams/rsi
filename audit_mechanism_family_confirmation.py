"""Independent audit of the family-inference confirmation.

Uses neither the runner's task masks nor its simulator. Reads the example
strings from the decision journal, rebuilds each task's constraints, and
checks: the catalog digest and journal hashes; every total, contrast and gate
recomputed from the journal alone; every pick consistent with its visible
examples and its hit equal to correctness on the hidden ones; a sample of picks
through the host interpreter; no tested mechanism in the prior's solved set,
and each stream matching its journal; and sampled lifetimes of both arms
replayed decision for decision by `rsi/family_reference.py`, which sorts the
whole catalog for every task.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict

import numpy as np

from rsi import coach_reference, family_reference
from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Prior
from rsi.mechanism_space import render_program
from rsi.mechanism_worlds import Harness
from rsi.semantic_invention import evaluate_program
from audit_mechanism_coach_confirmation import rebuilt_view
from mechanism_family_confirmation import (BUDGETS, DEST, OUT, SLIP, SPLITS, WEIGHT,
                                           family_coach, gates, paired)

AUDIT = ROOT / 'analysis/audit-mechanism-family-confirmation-20260923.json'
INTERPRETER_SAMPLE = 3000
LIFETIME_SAMPLE = 4
SEED = 973001


def main():
    if AUDIT.exists():
        raise RuntimeError('audit exists')
    started = time.perf_counter()
    analysis = json.loads(OUT.read_text())
    harness = Harness()
    keys_of_row = coach_reference.row_keys(harness)
    rng = random.Random(SEED)
    failures = []
    if harness.catalog.digest() != analysis['catalog']['digest']:
        failures.append('catalog digest differs')
    report = {'scope': 'independent audit of mechanism-family-confirmation-20260923',
              'catalog_digest': harness.catalog.digest(), 'replications': {}}

    for number, block in analysis['replications'].items():
        path = DEST / f'decisions-{number}.jsonl'
        if hashlib.sha256(path.read_bytes()).hexdigest() != block['decisions_sha256']:
            failures.append(f'{number}: journal hash differs')
        tasks, decisions = {}, defaultdict(list)
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                if row['kind'] == 'task':
                    tasks[(row['world'], row['step'])] = row
                else:
                    decisions[(row['world'], row['arm'], row['budget'])].append(row)

        totals = {split: {} for split in SPLITS}
        for split in SPLITS:
            worlds = [world['key'] for world in block['worlds'][split]]
            for arm in ('champion', 'family'):
                totals[split][arm] = np.array([[
                    sum(d['hit'] for d in decisions[(world, arm, budget)])
                    for budget in BUDGETS] for world in worlds])
                if totals[split][arm].tolist() != block['totals'][split][arm]:
                    failures.append(f'{number}/{split}/{arm}: totals differ')
        contrasts = {split: paired(totals[split]['family'], totals[split]['champion'],
                                   block['seed'] + 3) for split in SPLITS}
        if contrasts != block['contrasts']:
            failures.append(f'{number}: contrasts differ')
        if gates(contrasts) != block['gates']:
            failures.append(f'{number}: gates differ')

        views = {key: rebuilt_view(harness, task) for key, task in tasks.items()}
        picks, inconsistent, misgraded = [], 0, 0
        for (world, _arm, _budget), rows in decisions.items():
            for d in rows:
                if d['pick'] < 0:
                    misgraded += d['hit']
                    continue
                mask = harness.catalog.masks[d['pick']]
                vpos, vneg, hpos, hneg = views[(world, d['step'])]['masks']
                inconsistent += (mask & vpos) != vpos or bool(mask & vneg)
                misgraded += int((mask & hpos) == hpos and not mask & hneg) != d['hit']
                picks.append((world, d['step'], d['pick'], d['hit']))
        if inconsistent:
            failures.append(f'{number}: {inconsistent} picks inconsistent with visible examples')
        if misgraded:
            failures.append(f'{number}: {misgraded} hits disagree with rebuilt constraints')

        unsound = conservative = 0
        for world, step, pick, hit in rng.sample(picks, min(INTERPRETER_SAMPLE, len(picks))):
            task = tasks[(world, step)]
            program = render_program(harness.catalog.expr(pick))
            unsound += not evaluate_program(program, task['visible'])
            accepted = evaluate_program(program, task['hidden'])
            unsound += bool(hit and not accepted)
            conservative += bool(accepted and not hit)
        if unsound:
            failures.append(f'{number}: {unsound} sampled picks the interpreter contradicts')

        solved = {index for chosen in block['prior_solved'] for index in chosen}
        leaked = broken = 0
        for split in SPLITS:
            for world in block['worlds'][split]:
                leaked += len(solved & set(world['stream']))
                broken += [tasks[(world['key'], s)]['mechanism']
                           for s in range(len(world['stream']))] != world['stream']
        if leaked:
            failures.append(f'{number}: {leaked} tested mechanisms in the prior pool')
        if broken:
            failures.append(f'{number}: {broken} streams differ from the journal')

        harness.set_tiebreak(block['seed'] + 77)
        prior = Prior(harness, [sorted({harness.key_index[k] for k in harness.observed_keys(c)})
                                for c in block['prior_solved']])
        replayed = disagreements = 0
        for split in SPLITS:
            for world in rng.sample(block['worlds'][split], LIFETIME_SAMPLE):
                life = [views[(world['key'], s)] for s in range(len(world['stream']))]
                for arm in ('family', 'champion'):
                    budget = rng.choice(BUDGETS)
                    if arm == 'family':
                        expected = family_reference.lifetime(
                            harness, keys_of_row, life, prior, family_coach(budget), budget,
                            family=(WEIGHT, SLIP))
                    else:
                        expected = family_reference.lifetime(harness, keys_of_row, life, prior,
                                                             CHAMPION, budget)
                    recorded = [(d['pick'], d['hit']) for d in
                                sorted(decisions[(world['key'], arm, budget)],
                                       key=lambda d: d['step'])]
                    replayed += 1
                    disagreements += expected != recorded
        if disagreements:
            failures.append(f'{number}: {disagreements} of {replayed} replayed lifetimes differ')

        report['replications'][number] = {
            'picks': len(picks), 'interpreter_sample': min(INTERPRETER_SAMPLE, len(picks)),
            'interpreter_accepts_graded_misses': conservative, 'lifetimes_replayed': replayed,
            'gates_recomputed': gates(contrasts)}
        print(f'replication {number}: {len(picks)} picks checked, {replayed} lifetimes replayed, '
              f'{conservative} conservative gradings', flush=True)

    report['failures'] = failures
    report['passed'] = not failures
    report['wall_seconds'] = time.perf_counter() - started
    write_json(AUDIT, report)
    print('audit', 'passed' if not failures else 'FAILED', failures)


if __name__ == '__main__':
    main()
