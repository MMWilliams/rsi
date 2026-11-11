"""Counts behind the papers' limitations, read from committed ledgers, checks and
logs with no scoring: the denominators of the meta-tests, whether the procedure
changes adopted as cheaper saved anything over a whole run (against the
meta-off full arm), the gates on the eight seeds frozen in advance, what each
arm cost in seconds and invention tests beside scans, the paper's own gates
applied to each arm, how often an arm retired the model fallback, and how often
a cross-area check reused a set an earlier proof of that area had used."""
import json
import re
import statistics
from collections import Counter

from rsi.common import ROOT, write_json
from summarize_arms import ARMS, TAGS
from summarize_v11_replication import GROWTH, SEEDS

SECONDS = re.compile(r'; (\d+) s$', re.M)


def load(path):
    return json.loads((ROOT / path).read_text())


def ledger(name):
    return load(f'seeds/{name}/state.json')['ledger']


def meta_tests():
    """A meta-test runs two branches on one set; identical hits on every world
    mean the changed setting never altered an outcome there."""
    run = [e for name in SEEDS for e in ledger(name) if e['op'] == 'meta' and not e.get('noop')]
    differing = [e for e in run if e['meta']['ha'] != e['meta']['hb']]
    rules = Counter(e['rule'] for e in run if e['adopted'])
    return {'run': len(run), 'identical': len(run) - len(differing), 'differing': len(differing),
            'adopted': sum(rules.values()), 'adopted_by_rule': dict(rules),
            'adopted_among_identical': sum(e['adopted'] and e not in differing for e in run),
            'adopted_better_among_differing': sum(e['adopted'] and e['rule'] == 'better' for e in differing)}


def whole_run():
    """The sealed run (meta-level on) against the full arm (meta-level off) on
    the same seed: level-0 proof scans, and what the meta-tests cost on top."""
    out = {}
    for tag in TAGS:
        sealed, arm = load(f'seeds/{tag}/state.json'), load(f'seeds/full_{tag}/state.json')
        meta = [e for e in sealed['ledger'] if e['op'] == 'meta']
        charged = sum(e.get('charged', 0) for e in meta)
        level0, off = sealed['resource']['proof_scans'] - charged, arm['resource']['proof_scans']
        out[tag] = {'adopted': [f"{e['mutation']['knob']}={e['mutation']['after']} ({e['rule']})" for e in meta if e.get('adopted')],
                    'level0_proof_scans': level0, 'meta_off_proof_scans': off, 'level0_change': level0 / off - 1,
                    'meta_test_scans': charged, 'meta_share_of_meta_off_proofs': charged / off,
                    'same_kept_changes': sealed['kept'] == arm['kept']}
    return out


def reexecution():
    """Seed 919127 adopted no procedure change, so the full arm (meta-level off,
    run from scratch two weeks later with other worker counts) re-executes the
    sealed run c24 end to end."""
    sealed, arm = load('seeds/c24/state.json'), load('seeds/full_c24/state.json')
    entries = [[e for e in s['ledger'] if e['op'] in ('live', 'prove')] for s in (sealed, arm)]
    return {'live_and_prove_entries': len(entries[0]), 'equal_entries': sum(a == b for a, b in zip(*entries)),
            'same_length': len(entries[0]) == len(entries[1]),
            'same_language_kept_experience': all(sealed[k] == arm[k] for k in ('language', 'kept', 'experience')),
            'same_fresh_check': load('analysis/seed-check-c24.json')['areas'] == load('analysis/seed-check-full_c24.json')['areas']}


def arm_costs():
    out = {}
    for arm in ARMS:
        seconds, tests, scans = [], [], []
        for tag in TAGS:
            logs = sorted(ROOT.glob(f'runs_arms_{arm}_{tag}*.log'))   # a resumed run has a part1 log
            seconds.append(sum(int(s) for log in logs for s in SECONDS.findall(log.read_text())))
            r = load(f'seeds/{arm}_{tag}/state.json')['resource']
            tests.append(r['invention_tests'])
            scans.append(r['live_scans'] + r['proof_scans'])
        out[arm] = {'life_seconds': seconds, 'mean_life_seconds': statistics.mean(seconds),
                    'mean_invention_tests': statistics.mean(tests), 'mean_scans': statistics.mean(scans)}
    for a in out.values():
        a['seconds_vs_full'] = a['mean_life_seconds'] / out['full']['mean_life_seconds']
        a['scans_vs_full'] = a['mean_scans'] / out['full']['mean_scans']
    return out


def arm_gates():
    """Gate 1 (every area up 15%) and the lowest pool ratio, per arm."""
    arms = load('analysis/review002-arms.json')['arms']
    return {arm: {'gate1_seeds': sum(all(v['carried']['total'] / v['start']['total'] >= GROWTH
                                         for v in load(f'analysis/seed-check-{arm}_{tag}.json')['areas'].values()) for tag in TAGS),
                  'min_pool_ratio': min(r['min_pool_ratio'] for r in arms[arm]['runs'].values())} for arm in ARMS}


def retired_model():
    """Lives entered with the model fallback retired by the level-1 policy."""
    return {arm: [sum(e['op'] == 'revise' and 'model' not in e['active'] for e in ledger(f'{arm}_{tag}')) for tag in TAGS]
            for arm in ('full', 'frequency', 'no-invention')}


def reused_sets():
    """A cross-area check draws the checked area's set with the proposer's salt;
    count the checks whose salt an earlier proof in the checked area had used."""
    checks = reused = 0
    for name in SEEDS:
        own = {}
        for e in ledger(name):
            if e['op'] != 'prove':
                continue
            for other in e.get('elsewhere') or {}:
                checks += 1
                reused += e['salt'] in own.get(other, ())
            own.setdefault(e['area'], set()).add(e['salt'])
    return {'cross_area_checks': checks, 'reused_salt': reused}


def main():
    frozen = [s for s in load('analysis/review002-replication.json')['seeds'] if s['name'] not in ('c22', 'c23')]
    out = {'meta_tests': meta_tests(), 'whole_run': whole_run(), 'reexecution': reexecution(),
           'frozen_in_advance': {'seeds': len(frozen), 'pass_1_to_4': sum(s['passes_1_to_4'] for s in frozen)},
           'arm_costs': arm_costs(), 'arm_gates': arm_gates(), 'retired_model_fallback': retired_model(),
           'reused_sets': reused_sets()}
    write_json(ROOT / 'analysis/review002-limits.json', out)
    print(json.dumps({k: v for k, v in out.items() if k != 'arm_costs'}, indent=1))
    for arm, a in out['arm_costs'].items():
        print(f'{arm:13s} {a["mean_life_seconds"]:6.0f} s ({a["seconds_vs_full"]:.2f}x full)  scans {a["scans_vs_full"]:.2f}x  '
              f'invention tests {a["mean_invention_tests"] / 1e6:.1f}M')


if __name__ == '__main__':
    main()
