"""Independent audit of the coach confirmation.

The runner decides every task with masks it built while generating the task,
through the fast simulator in `rsi.growth_coach`. This audit uses neither. It
reads the example strings from the decision journal, rebuilds each task's
constraints from them, and checks:

1. the catalog rebuilds to the recorded digest, and each journal hashes to the
   value recorded in the analysis;
2. the deployment decision recomputes from the recorded validation totals, and
   every per-world total, paired contrast and gate recomputes from the journal
   alone, with the runner's bootstrap seeds;
3. every recorded pick reproduces its visible examples under the rebuilt
   constraints, and its recorded hit equals correctness on the hidden ones;
4. on a random sample of picks, the rendered program reproduces the visible
   examples through the host interpreter `evaluate_program`, and no pick graded
   correct is rejected by the interpreter on the hidden examples (grading is
   sound; the reverse, conservative, direction is counted);
5. no mechanism tested in an evaluation world is among the solved mechanisms
   the prior was built from, and each world's recorded stream matches its
   journal;
6. on a sample of lifetimes, `rsi.coach_reference`, which sorts the whole
   catalog for every task and merges with `interleave`, makes the same pick as
   the journal at every step, for the deployed policy (the coach where it was
   deployed, the champion elsewhere) and for the champion.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict

import numpy as np

from rsi import coach_reference
from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Coach, Prior
from rsi.mechanism_space import ALPHABET_BASE, render_program, vector_test
from rsi.mechanism_worlds import Harness
from rsi.semantic_invention import evaluate_program
from mechanism_coach_confirmation import (BUDGETS, DEST, OUT, SPLITS, deployment, gates,
                                          paired)

AUDIT = ROOT / 'analysis/audit-mechanism-coach-confirmation-20260923.json'
INTERPRETER_SAMPLE = 3000
LIFETIME_SAMPLE = 4
SEED = 943001


def constraints(examples):
    pos = neg = 0
    for text, target in examples:
        assert text.startswith(target) and len(target) < len(text)
        for char in target:
            pos |= 1 << (ord(char) - ALPHABET_BASE)
        neg |= 1 << (ord(text[len(target)]) - ALPHABET_BASE)
    return pos, neg


def rebuilt_view(harness, task):
    """A task view built from its strings, never from the runner's masks."""
    visible_pos, visible_neg = constraints(task['visible'])
    hidden_pos, hidden_neg = constraints(task['hidden'])
    consistent = np.flatnonzero(vector_test(harness.packed, visible_pos, visible_neg))
    good = vector_test(harness.packed, hidden_pos, hidden_neg)[consistent]
    select = np.lexsort((harness.complexity[consistent], harness.sizes[consistent]))
    return {'mechanism': task['mechanism'], 'rows': consistent[select], 'good': good[select],
            'masks': (visible_pos, visible_neg, hidden_pos, hidden_neg)}


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
    report = {'scope': 'independent audit of mechanism-coach-confirmation-20260923',
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

        # 2. deployment, totals, contrasts and gates.
        if deployment(block['validation'], block['seed'] + 53) != block['deploy']:
            failures.append(f'{number}: deployment decision differs')
        totals = {split: {} for split in SPLITS}
        for split in SPLITS:
            worlds = [world['key'] for world in block['worlds'][split]]
            for arm in ('champion', 'coach'):
                totals[split][arm] = np.array([[
                    sum(d['hit'] for d in decisions[(world, arm, budget)])
                    for budget in BUDGETS] for world in worlds])
                if totals[split][arm].tolist() != block['totals'][split][arm]:
                    failures.append(f'{number}/{split}/{arm}: totals differ')
        contrasts = {split: paired(totals[split]['coach'], totals[split]['champion'],
                                   block['seed'] + 3) for split in SPLITS}
        if contrasts != block['contrasts']:
            failures.append(f'{number}: contrasts differ')
        if gates(contrasts) != block['gates']:
            failures.append(f'{number}: gates differ')

        # 3. every pick against constraints rebuilt from the strings.
        views = {key: rebuilt_view(harness, task) for key, task in tasks.items()}
        picks, inconsistent, misgraded = [], 0, 0
        for (world, arm, budget), rows in decisions.items():
            for d in rows:
                if d['pick'] < 0:
                    if d['hit']:
                        misgraded += 1
                    continue
                mask = harness.catalog.masks[d['pick']]
                visible_pos, visible_neg, hidden_pos, hidden_neg = views[(world, d['step'])]['masks']
                if (mask & visible_pos) != visible_pos or mask & visible_neg:
                    inconsistent += 1
                correct = (mask & hidden_pos) == hidden_pos and not mask & hidden_neg
                if int(correct) != d['hit']:
                    misgraded += 1
                picks.append((world, d['step'], d['pick'], d['hit']))
        if inconsistent:
            failures.append(f'{number}: {inconsistent} picks inconsistent with visible examples')
        if misgraded:
            failures.append(f'{number}: {misgraded} hits disagree with rebuilt constraints')

        # 4. the interpreter on a sample of picks.
        unsound, conservative = 0, 0
        for world, step, pick, hit in rng.sample(picks, min(INTERPRETER_SAMPLE, len(picks))):
            task = tasks[(world, step)]
            program = render_program(harness.catalog.expr(pick))
            if not evaluate_program(program, task['visible']):
                unsound += 1
            accepted = evaluate_program(program, task['hidden'])
            if hit and not accepted:
                unsound += 1
            if accepted and not hit:
                conservative += 1
        if unsound:
            failures.append(f'{number}: {unsound} sampled picks the interpreter contradicts')

        # 5. disjointness and stream integrity.
        solved = {index for chosen in block['prior_solved'] for index in chosen}
        leaked, broken = 0, 0
        for split in SPLITS:
            for world in block['worlds'][split]:
                leaked += len(solved & set(world['stream']))
                journal_stream = [tasks[(world['key'], s)]['mechanism']
                                  for s in range(len(world['stream']))]
                broken += journal_stream != world['stream']
        if leaked:
            failures.append(f'{number}: {leaked} tested mechanisms in the prior pool')
        if broken:
            failures.append(f'{number}: {broken} streams differ from the journal')

        # 6. the direct semantics on sampled lifetimes.
        harness.set_tiebreak(block['seed'] + 77)
        observed = [sorted({harness.key_index[key] for key in harness.observed_keys(chosen)})
                    for chosen in block['prior_solved']]
        prior = Prior(harness, observed)
        coach = Coach(**block['coach'])
        replayed, disagreements = 0, 0
        for split in SPLITS:
            for world in rng.sample(block['worlds'][split], LIFETIME_SAMPLE):
                key = world['key']
                life = [views[(key, s)] for s in range(len(world['stream']))]
                for arm in ('coach', 'champion'):
                    budget = rng.choice(BUDGETS)
                    deployed = arm == 'coach' and block['deploy'][BUDGETS.index(budget)]
                    chosen = coach if deployed else CHAMPION
                    expected = coach_reference.lifetime(harness, keys_of_row, life, prior,
                                                        chosen, budget)
                    recorded = [(d['pick'], d['hit']) for d in
                                sorted(decisions[(key, arm, budget)], key=lambda d: d['step'])]
                    replayed += 1
                    disagreements += expected != recorded
        if disagreements:
            failures.append(f'{number}: {disagreements} of {replayed} replayed lifetimes differ')

        report['replications'][number] = {
            'decisions': sum(len(v) for v in decisions.values()), 'picks': len(picks),
            'interpreter_sample': min(INTERPRETER_SAMPLE, len(picks)),
            'interpreter_accepts_graded_misses': conservative,
            'lifetimes_replayed': replayed, 'gates_recomputed': gates(contrasts)}
        print(f'replication {number}: {len(picks)} picks checked, '
              f'{replayed} lifetimes replayed, {conservative} conservative gradings', flush=True)

    report['failures'] = failures
    report['passed'] = not failures
    report['wall_seconds'] = time.perf_counter() - started
    write_json(AUDIT, report)
    print('audit', 'passed' if not failures else 'FAILED', failures)


if __name__ == '__main__':
    main()
