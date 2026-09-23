"""Development-only test of retained ranker updates from verified bank feedback."""
from __future__ import annotations

import json
import time

import numpy as np
import torch

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_transfer import choose
from listwise_evaluator_development import Ranker
import seed_growth


RUN = ROOT / 'runs/listwise-evaluator-transfer-20260917'
SOURCE = ROOT / 'analysis/mixed-evaluator-source.json'
CHECKPOINT = ROOT / 'analysis/listwise-evaluator-development-v2.json'
OUT = ROOT / 'analysis/incremental-ranker-feedback-development.json'
VARIANTS = {
    'all_10_lr1e4': (10, 1e-4, False),
    'all_30_lr1e4': (30, 1e-4, False),
    'all_30_lr3e4': (30, 3e-4, False),
    'head_30_lr3e4': (30, 3e-4, True),
}


def load_base():
    v = json.loads(CHECKPOINT.read_text(encoding='utf-8'))['variants']['mlp32']
    mean = np.asarray(v['normalization_mean'], dtype=np.float32)
    scale = np.asarray(v['normalization_scale'], dtype=np.float32)
    state = {key: torch.tensor(value, dtype=torch.float32)
             for key, value in v['checkpoint_weights']['120'].items()}
    return mean, scale, state


def records():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    rows = []
    for task in tasks:
        candidates = pools[task['id']]
        x = representation({'id': task['id'], 'visible': task['visible']},
                           candidates)['structural'].astype(np.float32)
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in candidates]
        rows.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                     'structural': x, 'labels': labels,
                     'programs': [row['program'] for row in candidates], 'n': len(candidates)})
    return rows


def new_model(state, device):
    model = Ranker(32).to(device)
    model.load_state_dict(state)
    return model


def fit(state, mean, scale, rows, epochs, lr, head_only, device,
        scramble=False, seed=0):
    model = new_model(state, device)
    if head_only:
        for parameter in model.layers[0].parameters():
            parameter.requires_grad = False
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=.001)
    x = np.concatenate([row['structural'] for row in rows])
    y = np.concatenate([np.asarray(row['labels'], dtype=bool) for row in rows])
    if scramble:
        rng = np.random.default_rng(seed)
        left = 0
        for row in rows:
            right = left + row['n']
            rng.shuffle(y[left:right])
            left = right
    tx = torch.from_numpy((x - mean) / scale).to(device)
    ty = torch.from_numpy(y).to(device)
    offsets = np.cumsum([0, *(row['n'] for row in rows)])
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(tx)
        losses = []
        for left, right in zip(offsets[:-1], offsets[1:]):
            mask = ty[left:right]
            if not bool(mask.any()) or bool(mask.all()):
                continue
            values = logits[left:right]
            losses.append(torch.logsumexp(values, 0) - torch.logsumexp(values[mask], 0))
        torch.stack(losses).mean().backward()
        optimizer.step()
    model.eval()
    return model


def evaluate(model, mean, scale, rows, device):
    out = []
    with torch.no_grad():
        for row in rows:
            x = torch.from_numpy((row['structural'] - mean) / scale).to(device)
            scores = model(x).cpu().numpy()
            index = choose(scores, [{'program': p} for p in row['programs']])
            out.append(bool(row['labels'][index]))
    return sum(out)


def main():
    seed_growth.structure = bool_safe_structure
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    mean, scale, state = load_base()
    start = time.perf_counter()
    rows = records()
    source = json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    source_rows = [{**row, 'structural': np.asarray(row['structural'], dtype=np.float32)}
                   for row in source]
    seeds = sorted({row['seed'] for row in rows})
    episodes = []
    for j, train_seed in enumerate(seeds):
        test_seed = seeds[(j + 1) % len(seeds)]
        train_rows = [row for row in rows if row['seed'] == train_seed]
        test_rows = [row for row in rows if row['seed'] == test_seed]
        base = new_model(state, device).eval()
        scores = {'base': evaluate(base, mean, scale, test_rows, device)}
        for name, (epochs, lr, head_only) in VARIANTS.items():
            model = fit(state, mean, scale, train_rows, epochs, lr,
                        head_only, device)
            scores[name] = evaluate(model, mean, scale, test_rows, device)
        scrambled = fit(state, mean, scale, train_rows, 30, 1e-4,
                        False, device, scramble=True, seed=train_seed)
        scores['scrambled_30_lr1e4'] = evaluate(scrambled, mean, scale, test_rows, device)
        continued = fit(state, mean, scale, source_rows, 30, 1e-4, False, device)
        scores['source_continue_30_lr1e4'] = evaluate(
            continued, mean, scale, test_rows, device)
        episodes.append({'feedback_seed': train_seed, 'test_seed': test_seed,
                         'feedback_tasks': len(train_rows),
                         'feedback_labels': sum(row['n'] for row in train_rows),
                         'test_tasks': len(test_rows), 'scores': scores})
    names = list(episodes[0]['scores'])
    summary = {'scope': 'development only; all six transfer banks previously inspected',
               'device': device, 'episodes': len(episodes),
               'feedback_candidate_labels': sum(row['feedback_labels'] for row in episodes),
               'test_tasks': sum(row['test_tasks'] for row in episodes),
               'aggregate': {name: sum(row['scores'][name] for row in episodes)
                             for name in names},
               'wall_seconds': time.perf_counter() - start}
    write_json(OUT, {'summary': summary, 'episodes': episodes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
