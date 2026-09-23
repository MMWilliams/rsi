"""Independent audit of the mechanism growth confirmation.

The runner decides correctness by two integer tests against constraint masks it
built while generating each task. This audit never uses those masks. It reads
the recorded examples, derives the constraints again from the strings, and for
a sample of decisions renders the chosen predicate as a program and runs it
through the host interpreter `evaluate_program`, which is the same path the
rest of the repository grades DSL work with.

Checks:

1. the catalog rebuilds to the digest recorded in the analysis;
2. each decision journal hashes to the value recorded in the analysis;
3. every reported rate and paired total recomputes from the journal alone;
4. every predeclared gate recomputes from the recomputed totals;
5. on a random sample, the chosen predicate reproduces the visible examples
   through the interpreter, and is never graded correct by the mask tests when
   the interpreter rejects it. The converse is not a failure and is measured
   instead: grading reads a predicate as the longest satisfying prefix, while
   the interpreter also accepts a first run beginning after position zero, so
   grading is sound and conservative and the audit reports by how much;
6. no tested mechanism appears in the experience pool used to choose for it;
7. for the experience-free set rule, the pick is the first consistent candidate
   inside the budget under an ordering rebuilt from the journal.

The meta arms' orderings are not rebuilt: they depend on 400 training worlds
drawn from the runner's random stream. Their picks are checked for consistency,
correctness and pool disjointness, and their totals are recomputed, which is
what every reported comparison rests on.
"""
from __future__ import annotations

import hashlib
import json
import random
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.mechanism_space import ALPHABET_BASE, render_program
from rsi.mechanism_worlds import Harness, ranks_of
from rsi.semantic_invention import evaluate_program
from mechanism_growth_confirmation import (ADAPT, BUDGETS, DEST, FREE, OUT, STATIC,
                                           ADAPTIVE, FLOOR, gates, summarise)

AUDIT = ROOT / 'analysis/audit-mechanism-growth-confirmation-20260921.json'
SAMPLE = 3000
SEED = 931001


def constraints(examples):
    """Rebuild a task's constraint masks from its strings alone."""
    pos = neg = 0
    for text, target in examples:
        assert text.startswith(target) and len(target) < len(text)
        for char in target:
            pos |= 1 << (ord(char) - ALPHABET_BASE)
        neg |= 1 << (ord(text[len(target)]) - ALPHABET_BASE)
    return pos, neg


def main():
    if AUDIT.exists():
        raise RuntimeError('audit exists')
    started = time.perf_counter()
    analysis = json.loads(OUT.read_text())
    harness = Harness()
    failures = []
    if harness.catalog.digest() != analysis['catalog']['digest']:
        failures.append('catalog digest differs from the analysis')

    rng = random.Random(SEED)
    report = {'scope': 'independent audit of mechanism-growth-confirmation-20260921',
              'catalog_digest': harness.catalog.digest(), 'replications': {}}

    for number, block in analysis['replications'].items():
        path = DEST / f'decisions-{number}.jsonl'
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != block['decisions_sha256']:
            failures.append(f'replication {number}: journal digest differs')
        harness.set_tiebreak(block['seed'] + 77)
        static_ranks = {
            'complexity': ranks_of(np.lexsort((harness.tiebreak, harness.complexity))),
            'density': ranks_of(np.lexsort((harness.tiebreak, np.abs(harness.density - .5))))}
        arms = list(STATIC) + [f'{name}:{k}' for k in ADAPT for name in ADAPTIVE]
        outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                    for split in block['splits']}

        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        interpreter_checks = 0
        order_checks = 0
        permissive = 0
        sample = set(rng.sample(range(len(rows)), min(SAMPLE, len(rows))))

        for position, row in enumerate(rows):
            visible_pos, visible_neg = constraints(row['visible'])
            hidden_pos, hidden_neg = constraints(row['hidden'])
            if row['mechanism'] in row['pool']:
                failures.append('tested mechanism appears in its own experience pool')
            for arm in arms:
                for budget in BUDGETS:
                    pick = row['picks'][arm][str(budget)]
                    if pick < 0:
                        outcomes[row['split']][arm][budget].append(0)
                        continue
                    mask = harness.catalog.masks[pick]
                    if (mask & visible_pos) != visible_pos or mask & visible_neg:
                        failures.append(f'{arm} chose a candidate inconsistent with the '
                                        f'visible examples at budget {budget}')
                    hit = int((mask & hidden_pos) == hidden_pos and not mask & hidden_neg)
                    outcomes[row['split']][arm][budget].append(hit)

            if position in sample:
                arm = f'free_set:{rng.choice(ADAPT)}'
                budget = rng.choice(BUDGETS)
                recorded = row['picks'][arm][str(budget)]
                for other_arm in [arm] + rng.sample(arms, 5):
                    for other_budget in (budget, rng.choice(BUDGETS)):
                        pick = row['picks'][other_arm][str(other_budget)]
                        if pick < 0:
                            continue
                        program = render_program(harness.catalog.expr(pick))
                        if not evaluate_program(program, row['visible']):
                            failures.append('interpreter rejects a pick on visible examples')
                        mask = harness.catalog.masks[pick]
                        graded = int((mask & hidden_pos) == hidden_pos
                                     and not mask & hidden_neg)
                        by_interpreter = int(bool(evaluate_program(program, row['hidden'])))
                        if graded and not by_interpreter:
                            failures.append('graded correct but the interpreter rejects it')
                        permissive += int(by_interpreter and not graded)
                        interpreter_checks += 1
                # rebuild the free_set ordering from the journal and repeat the scan
                k = int(arm.split(':')[1])
                counts = harness.key_counts(row['pool'][:k])
                order = harness.order_from_key_scores(np.log((counts > 0).astype(float) + FLOOR))
                position_of = ranks_of(order)
                from rsi.mechanism_space import vector_test
                consistent = np.flatnonzero(vector_test(harness.packed, visible_pos,
                                                        visible_neg))
                select = np.lexsort((harness.complexity[consistent],
                                     harness.sizes[consistent]))
                limit = harness.catalog.size if budget is None else budget
                rebuilt = -1
                ranked = position_of[consistent]
                for candidate in select:
                    if ranked[candidate] < limit:
                        rebuilt = int(consistent[candidate])
                        break
                if rebuilt != recorded:
                    failures.append(f'rebuilt pick {rebuilt} differs from recorded {recorded}')
                order_checks += 1

        recomputed = summarise(outcomes, arms, block['seed'])
        for split in block['splits']:
            for arm in arms:
                for budget in BUDGETS:
                    reported = block['splits'][split]['rate'][arm][str(budget)]
                    if abs(recomputed[split]['rate'][arm][str(budget)] - reported) > 1e-12:
                        failures.append(f'rate differs for {split} {arm} {budget}')
        recomputed_gates = gates(recomputed)
        for claim in ('G1', 'G2', 'G3'):
            if recomputed_gates[claim]['passed'] != block['gates'][claim]['passed']:
                failures.append(f'replication {number}: gate {claim} differs')
        report['replications'][number] = {
            'decisions': len(rows), 'journal_sha256': digest,
            'interpreter_checks': interpreter_checks, 'order_checks': order_checks,
            'interpreter_more_permissive': permissive,
            'permissive_rate': permissive / max(interpreter_checks, 1),
            'gates': {claim: recomputed_gates[claim]['passed'] for claim in ('G1', 'G2', 'G3')},
            'g1_free_set_minus_static': recomputed_gates['G1']['free_set_minus_static'],
            'g1_free_set_minus_wrong_world': recomputed_gates['G1']['free_set_minus_wrong_world'],
        }

    report['passed'] = not failures
    report['failures'] = failures[:40]
    report['failure_count'] = len(failures)
    report['wall_seconds'] = time.perf_counter() - started
    write_json(AUDIT, report)
    print('audit passed' if report['passed'] else f'audit FAILED ({len(failures)})')
    for number, block in report['replications'].items():
        print('replication {}: {} decisions, {} interpreter checks ({} where the '
              'interpreter is more permissive, {:.4f}), {} order checks, gates {}'.format(
                  number, block['decisions'], block['interpreter_checks'],
                  block['interpreter_more_permissive'], block['permissive_rate'],
                  block['order_checks'], block['gates']))
    for line in report['failures'][:10]:
        print(' ', line)
    print('{:.1f}s'.format(report['wall_seconds']))


if __name__ == '__main__':
    main()
