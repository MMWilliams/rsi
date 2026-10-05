"""Independent audit of the earned-group confirmation.

As the learned-group audit, plus the level that is new here: every training
world's earned atom set rebuilt from its journaled picks through the reference
key table and equal to the recorded set; all four groupings relearned (earned,
early, handed) or re-permuted and equal to the recorded labels; a sample of
earning lifetimes regenerated from their recorded streams, every pick checked
against constraints rebuilt from the example strings, and replayed decision for
decision by `rsi/learned_reference.py` with the blind coach.

`--dev SEED` audits a development rehearsal.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
import warnings
from collections import defaultdict

import numpy as np

from rsi import coach_reference, learned_reference
from rsi.common import ROOT, write_json
from rsi.growth_coach import BLIND, CHAMPION, Prior, Simulator, world_seed
from rsi.learned_groups import learn_groups
from rsi.mechanism_space import render_program
from rsi.mechanism_worlds import Harness
from rsi.semantic_invention import evaluate_program
from audit_mechanism_coach_confirmation import rebuilt_view
from mechanism_earned_confirmation import (ARMS, BUDGETS, DEST, EARLY_WORLDS, EARN_BUDGET,
                                           GROUP_CHOICES, GROUPED, MID_WORLDS, MINIMUM_PICKS, OUT,
                                           PRIOR_WORLDS, SLIP, SPLITS, WEIGHT, agent_coach,
                                           confident, earned_set, grouping, gates, paired, pooled)

AUDIT = ROOT / 'analysis/audit-mechanism-earned-confirmation-20261005.json'
INTERPRETER_SAMPLE = 3000
LIFETIME_SAMPLE = 3
EARN_SAMPLE = 6
SEED = 993001


def main():
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    out, dest, audit = OUT, DEST, AUDIT
    if sys.argv[1:2] == ['--dev']:
        out = ROOT / f'analysis/mechanism-earned-confirmation-dev-{sys.argv[2]}.json'
        dest = ROOT / f'runs/mechanism-earned-confirmation-dev-{sys.argv[2]}'
        audit = ROOT / f'analysis/audit-mechanism-earned-confirmation-dev-{sys.argv[2]}.json'
    if audit.exists():
        raise RuntimeError('audit exists')
    started = time.perf_counter()
    analysis = json.loads(out.read_text())
    harness = Harness()
    simulator = Simulator(harness)
    keys_of_row = coach_reference.row_keys(harness)
    keys = len(harness.key_names)
    rng = random.Random(SEED)
    failures = []
    if harness.catalog.digest() != analysis['catalog']['digest']:
        failures.append('catalog digest differs')
    report = {'scope': f'independent audit of {out.name}',
              'catalog_digest': harness.catalog.digest(), 'replications': {}}

    for number, block in analysis['replications'].items():
        seed = block['seed']
        path = dest / f'decisions-{number}.jsonl'
        if hashlib.sha256(path.read_bytes()).hexdigest() != block['decisions_sha256']:
            failures.append(f'{number}: journal hash differs')

        tasks, decisions, earning = {}, defaultdict(list), {}
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                if row['kind'] == 'task':
                    tasks[(row['world'], row['step'])] = row
                elif row['kind'] == 'earn':
                    earning[row['world']] = row
                else:
                    decisions[(row['world'], row['arm'], row['budget'])].append(row)

        earned = [earned_set(earning[w]['decisions'], keys_of_row, MINIMUM_PICKS)
                  for w in range(len(earning))]
        if earned != block['earned_sets']:
            failures.append(f'{number}: earned sets do not rebuild from the journaled picks')
        handed = [sorted({harness.key_index[k] for k in harness.observed_keys(chosen)})
                  for chosen in block['training_solved']]
        labels = {}
        for name, sets in (('earned', confident(earned)), ('mid', confident(earned[:MID_WORLDS])),
                           ('early', confident(earned[:EARLY_WORLDS])), ('handed', handed)):
            labels[name], _count = grouping(sets, keys)
        labels['permuted'] = None if labels['earned'] is None else \
            labels['earned'][np.random.default_rng(seed + 9).permutation(keys)]
        for name in GROUPED:
            if (None if labels[name] is None else labels[name].tolist()) != block['labels'][name]:
                failures.append(f'{number}: {name} groups do not relearn to the recorded labels')

        # Earning: the world's own atoms can only enter through its picks, and
        # the picks must be the blind loop's on the regenerated tasks.
        harness.set_tiebreak(seed + 77)
        earn_checked = earn_bad = earn_replay_bad = 0
        for w in rng.sample(range(len(earning)), EARN_SAMPLE):
            stream_ = earning[w]['stream']
            raw = simulator.views(stream_, random.Random(world_seed(seed + 5, w)), examples=True)
            life = [rebuilt_view(harness, {'mechanism': v['mechanism'], 'visible': v['visible'],
                                           'hidden': v['hidden']}) for v in raw]
            for (pick, hit), view in zip(earning[w]['decisions'], life):
                earn_checked += 1
                if pick < 0:
                    earn_bad += hit
                    continue
                mask = harness.catalog.masks[pick]
                vpos, vneg, hpos, hneg = view['masks']
                earn_bad += (mask & vpos) != vpos or bool(mask & vneg)
                earn_bad += int((mask & hpos) == hpos and not mask & hneg) != hit
            expected = learned_reference.lifetime(harness, keys_of_row, life, None, BLIND,
                                                  EARN_BUDGET)
            earn_replay_bad += [tuple(d) for d in earning[w]['decisions']] != \
                [tuple(d) for d in expected]
        if earn_bad:
            failures.append(f'{number}: {earn_bad} earning picks inconsistent or misgraded')
        if earn_replay_bad:
            failures.append(f'{number}: {earn_replay_bad} of {EARN_SAMPLE} earning lifetimes differ')

        totals = {split: {} for split in SPLITS}
        for split in SPLITS:
            worlds = [world['key'] for world in block['worlds'][split]]
            for arm in ARMS:
                totals[split][arm] = np.array([[
                    sum(d['hit'] for d in decisions[(world, arm, budget)])
                    for budget in BUDGETS] for world in worlds])
                if totals[split][arm].tolist() != block['totals'][split][arm]:
                    failures.append(f'{number}/{split}/{arm}: totals differ')
        contrasts = {arm: {split: paired(totals[split][arm], totals[split]['champion'], seed + 3)
                           for split in SPLITS} for arm in GROUPED}
        grown = pooled(totals, 'earned', 'early', seed + 4)
        structure = pooled(totals, 'earned', 'permuted', seed + 5)
        if contrasts != block['contrasts'] or grown != block['growth'] \
                or structure != block['structure']:
            failures.append(f'{number}: contrasts, growth or structure differ')
        recomputed = gates(contrasts['earned'], grown, structure)
        if recomputed != block['gates']:
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

        tested = {index for split in SPLITS for world in block['worlds'][split]
                  for index in world['stream']}
        solved = {index for chosen in block['training_solved'] for index in chosen}
        earned_streams = {index for row in earning.values() for index in row['stream']}
        leaked = len(tested & solved) + len(tested & earned_streams)
        broken = sum([tasks[(world['key'], s)]['mechanism'] for s in range(len(world['stream']))]
                     != world['stream'] for split in SPLITS for world in block['worlds'][split])
        if leaked:
            failures.append(f'{number}: {leaked} tested mechanisms among training worlds')
        if broken:
            failures.append(f'{number}: {broken} streams differ from the journal')

        prior = Prior(harness, handed[:PRIOR_WORLDS])
        replayed = disagreements = 0
        for split in SPLITS:
            for world in rng.sample(block['worlds'][split], LIFETIME_SAMPLE):
                life = [views[(world['key'], s)] for s in range(len(world['stream']))]
                for arm in ARMS:
                    budget = rng.choice(BUDGETS)
                    if arm == 'champion' or labels[arm] is None:
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
                    disagreements += [tuple(e) for e in expected] != recorded
        if disagreements:
            failures.append(f'{number}: {disagreements} of {replayed} replayed lifetimes differ')

        report['replications'][number] = {
            'earning_picks_checked': earn_checked, 'earning_lifetimes_replayed': EARN_SAMPLE,
            'picks': len(picks), 'interpreter_sample': min(INTERPRETER_SAMPLE, len(picks)),
            'interpreter_accepts_graded_misses': conservative, 'lifetimes_replayed': replayed,
            'gates_recomputed': recomputed}
        print(f'replication {number}: {earn_checked} earning picks, {len(picks)} picks checked, '
              f'{replayed} lifetimes replayed, {conservative} conservative gradings', flush=True)

    report['failures'] = failures
    report['passed'] = not failures
    report['wall_seconds'] = time.perf_counter() - started
    write_json(audit, report)
    print('audit', 'passed' if not failures else 'FAILED', failures)


if __name__ == '__main__':
    main()
