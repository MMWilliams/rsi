"""The time-matched arm: accept-all given the full arm's wall-clock time, not its
scans. In each step of the schedule it keeps living until its own seconds reach
the full arm's seconds at the end of the same step on the same seed, with at
least one life per step. A life's seconds are what run_arms.py prints: living
plus the proposal phase. The seconds of every life and the lives of every step
are saved in the state, so a killed run resumes and the realised schedule can be
run again. Usage: run_time_matched.py <tag> <seed>; state goes to
seeds/time-matched_<tag>; --of names the arm whose log holds the clock.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import warnings

import seed_check
import seed_run
from run_arms import BUDGET, SCHEDULE, lives_of, wait_for_commit
from rsi.common import ROOT
from rsi.invention import candidates
from rsi.seed import MechanismArea, make_area
from rsi.seed_arms import AcceptAll
from rsi.seed_string import SEED_LANGUAGE


def targets(log, steps):
    """The reference arm's cumulative seconds at the end of each step."""
    seconds = [int(s) for s in re.findall(r'; (\d+) s$', log.read_text(), re.M)]
    assert len(seconds) == sum(n for _, n in steps), f'{log.name}: {len(seconds)} lives timed, schedule has {sum(n for _, n in steps)}'
    out, done = [], 0
    for _, lives in steps:
        done += lives
        out.append(sum(seconds[:done]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('seed', type=int)
    ap.add_argument('--of', default='full')
    ap.add_argument('--schedule', default=SCHEDULE)
    ap.add_argument('--worlds', type=int, default=96)
    ap.add_argument('--held-out', type=int, default=48)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    steps = lives_of(args.schedule)
    goal = targets(ROOT / f'runs_arms_{args.of}_{args.tag}.log', steps)
    name = f'time-matched_{args.tag}'
    seed = AcceptAll(ROOT / 'seeds' / name, language=MechanismArea(args.seed).seed_language + SEED_LANGUAGE, name=name, seed=args.seed)
    seed.state.update(arm='time-matched', reference=goal)   # the clock it was matched to, for the summary
    clock = seed.state.setdefault('clock', [])   # seconds of every life lived
    plan = seed.state.setdefault('plan', [])     # lives lived in every finished step
    seed.save()
    cands = candidates()
    for i, (area_name, _) in enumerate(steps):
        if i < len(plan):
            continue
        area = make_area(area_name, args.seed)
        before = sum(n for (a, _), n in zip(steps, plan) if a == area_name)
        while seed.lives(area_name) == before or sum(clock) < goal[i]:
            wait_for_commit()
            t = time.time()
            life, worlds, records = seed.live(area, args.worlds, BUDGET)
            solved = seed.state['ledger'][-1]['total']
            seed_run.phase(seed, area, worlds, records, cands, BUDGET, args.held_out)
            clock.append(round(time.time() - t, 1))
            seed.save()
            print(f'{area_name} life {life}: solved {solved}, version {seed.state["version"]}, language {len(seed.state["language"])}; '
                  f'{clock[-1]:.0f} s, {sum(clock):.0f} of {goal[i]}', flush=True)
        plan.append(seed.lives(area_name) - before)
        seed.save()
    print(f'lives per step {plan}, {sum(clock):.0f} s against {goal[-1]}', flush=True)
    sys.argv = ['seed_check', '--name', name, '--seed', str(args.seed), '--areas', ','.join(dict.fromkeys(a for a, _ in steps))]
    seed_check.main()


if __name__ == '__main__':
    main()
