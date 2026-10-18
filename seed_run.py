"""Run the seed for some lives in one area and report what it kept.

Each life: live (earn in fresh worlds), then propose every change at once
(invented atoms, pruned atoms, a refit model and prior) and prove the
combination; if it fails, prove on its own each part the seed's fallback
policy, learned from its own ledger, still tests. Every proof is on a
held-out set drawn fresh for that life, and a change to the shared language
must also leave every other area the seed has lived in no worse.

With --meta-every N, every Nth life of the seed (counted over all areas)
it also tests a change to its own procedure (the knobs of its producer and
of the rule that revises the producer): two branches run the
proposal-and-proof phase from the same lived worlds, one under the current
procedure and one under the mutated one, and the mutation is adopted only
if the branch under it scores higher on a meta set no proof used, or
scores no lower at a tenth less cost. A knob that acts within a life is
tested over that life; one that acts across lives (patience, probation)
over --meta-lives K lives, the branches living the same world draws, and
only if the area's run has K lives left. With a horizon of one life, a
mutation that would propose and test exactly what the current procedure
proposes is a no-op: recorded, not run. The
state is saved after every operation, so a run resumes, and the ledger
records every candidate change with its proof.
"""
from __future__ import annotations

import argparse
import faulthandler
import json
import shutil
import sys
import time
import warnings

import numpy as np

from rsi.common import ROOT
from rsi.invention import candidates
from rsi.seed import SECOND_ORDER, MechanismArea, Seed, form_of, make_area
from rsi.seed_string import SEED_LANGUAGE

MARGIN = .1   # a mutation that scores no lower is adopted if it costs at least this much less


def fmt(score):
    return json.dumps({k: round(v, 1) for k, v in score['by_pool'].items()})


def report(tag, label, kept, carried, new, elsewhere):
    where = '' if not elsewhere else ' elsewhere ' + json.dumps(
        {k: f'{v["carried"]}->{v["candidate"]}' for k, v in elsewhere.items()})
    lo, hi = new.get('interval', (0., 0.))
    print(f'  {tag}{label}: held-out {carried["total"]} -> {new["total"]} [{lo:+.1f}, {hi:+.1f}] per world '
          f'{"KEPT" if kept else "dropped"}; {fmt(new)}{where}', flush=True)


def propose(seed, area, worlds, records, cands, tag):
    atoms, tests, provenance = seed.extend(worlds, records, cands)
    drop = seed.prune(form_of(area.spec))
    model = seed.reflect(area.name)
    if model and 'error' in model:
        print(f'  {tag}reflect: fit failed {model["error"]}', flush=True)
        model = None
    parts = {}
    if atoms:
        parts['extend'] = (f'language +{len(atoms)}', True,
                           {'tests': tests, 'atoms': [p['atom'] for p in provenance],
                            'from_pools': sorted({p['pool'] for p in provenance})})
    if drop:
        parts['prune'] = (f'prune -{len(drop)}', True, {'atoms': drop})
    if model:
        parts['model'] = (f'model g={model["groups"]} pw={model["per_world"]} from {model["worlds"]} worlds + prior',
                          False, None)
    return parts, atoms, drop, model


def test(seed, area, parts, atoms, drop, model, budget, held_out, tag):
    def fresh():
        # the held-out set changes only after an acceptance in this area, within a life
        # as across lives: a set on which nothing was accepted carries no selection bias,
        # and the carried score on it stays cached
        accepted = sum(1 for e in seed.state['ledger'] if e['op'] == 'prove' and e.get('kept') and e['area'] == area.name)
        salt = 1000 * (1 + sorted(seed.state['areas']).index(area.name)) + accepted
        return salt, area.held_out(-(-held_out // len(area.pools)), salt=salt)   # --held-out worlds over all pools

    def apply(cand, names):
        if 'extend' in names:
            cand['language'] += [list(a) for a in atoms]
            for a in atoms:
                cand['inventions'][a[0]] = {'life': seed.lives(), 'area': area.name}
        if 'prune' in names:
            cand['language'] = [a for a in cand['language'] if a[0] not in drop]
            for k in drop:
                cand['inventions'].pop(k, None)
        if 'model' in names:
            cand['areas'][area.name]['model'] = model
            cand['areas'][area.name]['prior'] = True
        return cand

    if not parts:
        print(f'  {tag}nothing to propose', flush=True)
        return
    done = False
    if len(parts) >= 2:
        cand = apply(seed.candidate(), set(parts))
        salt, held = fresh()
        kept, carried, new, elsewhere = seed.prove(
            area, held, salt, cand, budget, ' + '.join(p[0] for p in parts.values()),
            note={'parts': list(parts)}, shared=any(p[1] for p in parts.values()))
        report(tag, 'together', kept, carried, new, elsewhere)
        done = kept
    if done:
        return
    policy = seed.revise(area)
    if policy['retired']:
        print(f'  {tag}policy: fallbacks {policy["active"]}, retired {json.dumps(policy["retired"])}', flush=True)
    applied = set()
    for key in policy['active']:
        kinds = key.split('+')
        fresh_kinds = [k for k in kinds if k not in applied]
        if not fresh_kinds or any(k not in parts for k in kinds):
            continue
        cand = apply(seed.candidate(), set(fresh_kinds))
        salt, held = fresh()
        note = {'parts': kinds, 'fallback': True}
        for k in fresh_kinds:
            note.update(parts[k][2] or {})
        kept, carried, new, elsewhere = seed.prove(
            area, held, salt, cand, budget, ' + '.join(parts[k][0] for k in fresh_kinds),
            note=note, shared=any(parts[k][1] for k in fresh_kinds))
        report(tag, key, kept, carried, new, elsewhere)
        if kept:
            applied.update(fresh_kinds)


def phase(seed, area, worlds, records, cands, budget, held_out, tag=''):
    """Propose and prove under the seed's procedure."""
    test(seed, area, *propose(seed, area, worlds, records, cands, tag), budget, held_out, tag)


def plan(seed, area, proposal):
    """What a phase would propose and test: equal plans give identical phases."""
    parts, atoms, drop, model = proposal
    return (sorted(a[0] for a in atoms), sorted(drop), json.dumps(model, sort_keys=True) if model else None,
            seed.fallback_policy(form_of(area.spec))['active'] if parts else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--area', default='mech')
    ap.add_argument('--lives', type=int, default=4)
    ap.add_argument('--worlds', type=int, default=48)
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--held-out', type=int, default=48, help='worlds per acceptance test, over all pools')
    ap.add_argument('--meta-every', type=int, default=0,
                    help="test a change to the procedure every Nth of the seed's lives; 0 never")
    ap.add_argument('--meta-lives', type=int, default=1,
                    help='lives each branch runs before the meta set scores them, for knobs that act across lives')
    ap.add_argument('--meta-budget', type=float, default=0,
                    help='test the procedure only while its tests have cost less than this share of all proof scans; 0 no limit')
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    faulthandler.dump_traceback_later(600, repeat=True)   # where the main process is, if it stalls
    area = make_area(args.area, args.seed)
    mech = area if args.area == 'mech' else MechanismArea(args.seed)
    seed = Seed(ROOT / 'seeds' / args.name, language=mech.seed_language + SEED_LANGUAGE,
                name=args.name, seed=args.seed)
    if not any(a[1] == 'str' for a in seed.state['language']):   # a seed from before the string form
        for key in ('language', 'initial_language'):
            seed.state[key] += [list(a) for a in SEED_LANGUAGE]
        seed.state['ledger'].append({'op': 'vocabulary', 'area': 'str', 'atoms': len(SEED_LANGUAGE),
                                     'version': seed.state['version']})
        seed.save()
    cands = candidates()
    print(f'seed {seed.state["name"]} version {seed.state["version"]}, area {area.name}, lives there '
          f'{seed.lives(area.name)}, language {len(seed.state["language"])} atoms, '
          f'procedure {json.dumps(seed.procedure(form_of(area.spec)))}', flush=True)

    target = seed.lives(area.name) + args.lives
    while seed.lives(area.name) < target:
        t = time.time()
        life, worlds, records = seed.live(area, args.worlds, args.budget)
        entry = seed.state['ledger'][-1]
        print(f'{area.name} life {life}: solved {entry["total"]} of {args.worlds * 100}; by pool '
              f'{fmt(entry)}; {time.time() - t:.0f} s', flush=True)
        form = form_of(area.spec)
        due = args.meta_every and seed.lives() % args.meta_every == 0
        within = not args.meta_budget or seed.meta_spent() < args.meta_budget * seed.state['resource']['proof_scans']
        horizon = 0
        if due and within:
            knob, value, votes = seed.mutation(form)
            before = seed.procedure(form)[knob]
            horizon = args.meta_lives if knob in SECOND_ORDER else 1
            left = target - seed.lives(area.name) + 1
            print(f'  meta: {knob} {before} -> {value} over {horizon} lives; votes {json.dumps(votes)}', flush=True)
            if horizon > left:
                print(f'  meta: {left} lives left in this run; no test', flush=True)
                horizon = 0
        elif due:
            print(f'  meta: budget spent ({seed.meta_spent() / 1e6:.1f}M of '
                  f'{args.meta_budget * seed.state["resource"]["proof_scans"] / 1e6:.1f}M); no test', flush=True)
        if horizon:
            a, b = seed.branch('a'), seed.branch('b')
            b.state['procedure'][form][knob] = value
            b.save()
            prop_a = propose(a, area, worlds, records, cands, '[a] ')
            prop_b = propose(b, area, worlds, records, cands, '[b] ')
            if horizon == 1 and plan(a, area, prop_a) == plan(b, area, prop_b):
                # the same proposals under the same fallbacks: the phases would be identical
                shutil.rmtree(seed.path / 'branches', ignore_errors=True)
                seed.state['ledger'].append({'op': 'meta', 'area': area.name, 'form': form, 'life': life,
                                             'mutation': {'knob': knob, 'before': before, 'after': value, 'votes': votes},
                                             'noop': True})
                print(f'  meta: {knob}={value} changes nothing this life; not tested', flush=True)
                test(seed, area, *prop_a, args.budget, args.held_out, '')
                seed.state['resource']['invention_tests'] += a.state['resource']['invention_tests'] - seed.state['resource']['invention_tests']
                seed.save()
            else:
                base = dict(seed.state['resource'])
                test(a, area, *prop_a, args.budget, args.held_out, '[a] ')
                test(b, area, *prop_b, args.budget, args.held_out, '[b] ')
                for branch, tag in ((a, '[a] '), (b, '[b] ')):
                    for _ in range(horizon - 1):     # the horizon: the same world draws in both
                        life_, worlds_, records_ = branch.live(area, args.worlds, args.budget)
                        e_ = branch.state['ledger'][-1]
                        print(f'  {tag}{area.name} life {life_}: solved {e_["total"]} of {args.worlds * 100}', flush=True)
                        phase(branch, area, worlds_, records_, cands, args.budget, args.held_out, tag)
                cost_a = {k: a.state['resource'][k] - base[k] for k in base}
                cost_b = {k: b.state['resource'][k] - base[k] for k in base}
                meta = seed.meta_proof(area, a.state, b.state, args.budget, life + horizon - 1, args.held_out)
                mutation = {'knob': knob, 'before': before, 'after': value, 'votes': votes}
                diff = np.array(meta['hb'], dtype=float) - np.array(meta['ha'], dtype=float)
                pooled = seed.pooled(form, mutation, diff, cost_a['proof_scans'], cost_b['proof_scans'], meta['salt'])
                verdict = pooled or {'mean': meta['mean'], 'interval': meta['interval'],
                                     'cost': {'a': cost_a['proof_scans'], 'b': cost_b['proof_scans']}}
                lo, hi = verdict['interval']
                ca, cb = verdict['cost']['a'], verdict['cost']['b']
                better = lo > 0
                cheaper = verdict['mean'] >= 0 and lo <= 0 <= hi and cb <= ca * (1 - MARGIN)
                adopted = better or cheaper
                entry = {'op': 'meta', 'area': area.name, 'form': form, 'life': life, 'lives': horizon,
                         'budget': args.budget, 'mutation': mutation,
                         'cost': {'a': cost_a, 'b': cost_b}, 'meta': meta, 'adopted': adopted,
                         'rule': 'better' if better else 'cheaper' if cheaper else 'declined', 'margin': MARGIN,
                         **({'pooled': pooled} if pooled else {})}
                seed.adopt(b if adopted else a, a if adopted else b, entry)
                print(f'  meta: {meta["a"]} -> {meta["b"]} on {meta["worlds"]} worlds'
                      f'{" (pooled over %d tests, %d worlds)" % (pooled["tests"], pooled["worlds"]) if pooled else ""} '
                      f'[{lo:+.1f}, {hi:+.1f}] per world, proof cost {ca / 1e6:.1f}M vs {cb / 1e6:.1f}M: {knob}={value} '
                      f'{"ADOPTED (" + entry["rule"] + ")" if adopted else "declined"}', flush=True)
        else:
            phase(seed, area, worlds, records, cands, args.budget, args.held_out)
        a_ = seed.state['areas'][area.name]
        r = seed.state['resource']
        print(f'  carried: version {seed.state["version"]}, language {len(seed.state["language"])}, '
              f'model {"g=%d pw=%d" % (a_["model"]["groups"], a_["model"].get("per_world", 3)) if a_["model"] else "no"}, '
              f'prior {"yes" if a_["prior"] else "no"}, held-out {a_["held_out_score"]["total"]}; '
              f'procedure {json.dumps(seed.procedure(form))}; '
              f'resource live {r["live_scans"] / 1e6:.1f}M proof {r["proof_scans"] / 1e6:.1f}M '
              f'tests {r["invention_tests"]}; {time.time() - t:.0f} s', flush=True)
    print('kept:', json.dumps(seed.state['kept'][-12:]), flush=True)


if __name__ == '__main__':
    sys.exit(main())
