"""Independent audit of the learned-group confirmation.

Uses neither the runner's task masks nor its simulator. Checks: the catalog
digest and journal hashes; both learned groupings relearned from the recorded
training worlds and equal to the recorded labels; every total, contrast, growth
figure and gate recomputed from the journal alone; every pick consistent with
its visible examples and its hit equal to correctness on the hidden ones,
constraints rebuilt from the example strings; a sample of picks through the
host interpreter; no tested mechanism among the training worlds' solved
mechanisms, and each stream matching its journal; and sampled lifetimes of all
three arms replayed decision for decision by `rsi/learned_reference.py`, which
sorts the whole catalog for every task.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict

import numpy as np

from rsi import coach_reference, learned_reference
from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Prior
from rsi.learned_groups import learn_groups
from rsi.mechanism_space import render_program
from rsi.mechanism_worlds import Harness
from rsi.semantic_invention import evaluate_program
from audit_mechanism_coach_confirmation import rebuilt_view
from mechanism_learned_confirmation import (ARMS, BUDGETS, DEST, EARLY_WORLDS, GROUP_CHOICES,
                                            OUT, PRIOR_WORLDS, SLIP, SPLITS, TRAINING_WORLDS,
                                            WEIGHT, agent_coach, gates, growth, paired)

AUDIT = ROOT / 'analysis/audit-mechanism-learned-confirmation-20260923.json'
INTERPRETER_SAMPLE = 3000
LIFETIME_SAMPLE = 3
SEED = 983001


def main():
    if AUDIT.exists():
        raise RuntimeError('audit exists')
    started = time.perf_counter()
    analysis = json.loads(OUT.read_text())
    harness = Harness()
    keys_of_row = coach_reference.row_keys(harness)
    keys = len(harness.key_names)
    rng = random.Random(SEED)
    failures = []
    if harness.catalog.digest() != analysis['catalog']['digest']:
        failures.append('catalog digest differs')
    report = {'scope': 'independent audit of mechanism-learned-confirmation-20260923',
              'catalog_digest': harness.catalog.digest(), 'replications': {}}

    for number, block in analysis['replications'].items():
        path = DEST / f'decisions-{number}.jsonl'
        if hashlib.sha256(path.read_bytes()).hexdigest() != block['decisions_sha256']:
            failures.append(f'{number}: journal hash differs')

        observed = [sorted({harness.key_index[k] for k in harness.observed_keys(chosen)})
                    for chosen in block['training_solved']]
        labels = {}
        for name, size in (('learned', TRAINING_WORLDS), ('early', EARLY_WORLDS)):
            labels[name], _count = learn_groups(observed[:size], keys, choices=GROUP_CHOICES,
                                                select='likelihood')
            if labels[name].tolist() != block['labels'][name]:
                failures.append(f'{number}: {name} groups do not relearn to the recorded labels')

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
            for arm in ARMS:
                totals[split][arm] = np.array([[
                    sum(d['hit'] for d in decisions[(world, arm, budget)])
                    for budget in BUDGETS] for world in worlds])
                if totals[split][arm].tolist() != block['totals'][split][arm]:
                    failures.append(f'{number}/{split}/{arm}: totals differ')
        contrasts = {split: paired(totals[split]['learned'], totals[split]['champion'],
                                   block['seed'] + 3) for split in SPLITS}
        grown = growth(totals, block['seed'] + 4)
        if contrasts != block['contrasts'] or grown != block['growth']:
            failures.append(f'{number}: contrasts or growth differ')
        if gates(contrasts, grown) != block['gates']:
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

        solved = {index for chosen in block['training_solved'] for index in chosen}
        leaked = broken = 0
        for split in SPLITS:
            for world in block['worlds'][split]:
                leaked += len(solved & set(world['stream']))
                broken += [tasks[(world['key'], s)]['mechanism']
                           for s in range(len(world['stream']))] != world['stream']
        if leaked:
            failures.append(f'{number}: {leaked} tested mechanisms among training solved sets')
        if broken:
            failures.append(f'{number}: {broken} streams differ from the journal')

        harness.set_tiebreak(block['seed'] + 77)
        prior = Prior(harness, observed[:PRIOR_WORLDS])
        replayed = disagreements = 0
        for split in SPLITS:
            for world in rng.sample(block['worlds'][split], LIFETIME_SAMPLE):
                life = [views[(world['key'], s)] for s in range(len(world['stream']))]
                for arm in ARMS:
                    budget = rng.choice(BUDGETS)
                    if arm == 'champion':
                        expected = learned_reference.lifetime(harness, keys_of_row, life, prior,
                                                              CHAMPION, budget)
                    else:
                        expected = learned_reference.lifetime(
                            harness, keys_of_row, life, prior, agent_coach(budget), budget,
                            groups=(labels[arm], WEIGHT, SLIP))
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
            'gates_recomputed': gates(contrasts, grown)}
        print(f'replication {number}: {len(picks)} picks checked, {replayed} lifetimes replayed, '
              f'{conservative} conservative gradings', flush=True)

    report['failures'] = failures
    report['passed'] = not failures
    report['wall_seconds'] = time.perf_counter() - started
    write_json(AUDIT, report)
    print('audit', 'passed' if not failures else 'FAILED', failures)


if __name__ == '__main__':
    main()
