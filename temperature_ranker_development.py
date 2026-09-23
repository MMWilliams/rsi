"""Development search over listwise loss sharpness on the same verified labels."""
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
from listwise_evaluator_development import Ranker, pack
import seed_growth


SOURCE = ROOT / 'analysis/mixed-evaluator-source.json'
RUN = ROOT / 'runs/listwise-evaluator-transfer-20260917'
OUT = ROOT / 'analysis/temperature-ranker-development.json'
TEMPERATURES = (.25, .5, 1., 2., 4.)
EPOCHS = (80, 120)
SEED = 902532


def targets():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    result = []
    for task in tasks:
        rows = pools[task['id']]
        x = representation({'id': task['id'], 'visible': task['visible']},
                           rows)['structural']
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in rows]
        result.append({'id': task['id'], 'seed': task['seed'],
                       'family': task['family'], 'n': len(rows),
                       'programs': [row['program'] for row in rows],
                       'structural': x, 'labels': labels})
    return result


def score(model, mean, scale, rows, device):
    result = []
    model.eval()
    with torch.no_grad():
        for row in rows:
            x = np.asarray(row['structural'], dtype=np.float32)
            logits = model(torch.from_numpy((x - mean) / scale).to(device)).cpu().numpy()
            index = choose(logits, [{'program': program} for program in row['programs']])
            result.append({'id': row['id'], 'seed': row.get('seed'),
                           'family': row.get('family'), 'correct': bool(row['labels'][index])})
    return result


def train(temperature, source, mean, scale, device):
    torch.manual_seed(SEED)
    x, y, sizes = pack(source)
    tx = torch.from_numpy((x - mean) / scale).to(device)
    ty = torch.from_numpy(y).to(device)
    offsets = np.cumsum([0, *sizes])
    model = Ranker(32).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    snapshots = {}
    for epoch in range(1, max(EPOCHS) + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(tx)
        losses = []
        for left, right in zip(offsets[:-1], offsets[1:]):
            mask = ty[left:right]
            if not bool(mask.any()) or bool(mask.all()):
                continue
            values = logits[left:right] / temperature
            losses.append(temperature * (torch.logsumexp(values, 0) -
                                         torch.logsumexp(values[mask], 0)))
        torch.stack(losses).mean().backward()
        optimizer.step()
        if epoch in EPOCHS:
            snapshots[str(epoch)] = {key: value.detach().cpu().numpy().tolist()
                                     for key, value in model.state_dict().items()}
    return model, snapshots


def main():
    seed_growth.structure = bool_safe_structure
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    source = json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    x, _, _ = pack(source)
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), .05)
    start = time.perf_counter()
    target = targets()
    variants = {}
    for temperature in TEMPERATURES:
        model, snapshots = train(temperature, source, mean, scale, device)
        variants[str(temperature)] = {'target': score(model, mean, scale, target, device),
                                      'source': score(model, mean, scale, source, device),
                                      'weights': snapshots}
    families = sorted({row['family'] for row in target})
    summary = {'scope': 'development only; target labels inspected before this edit',
               'device': device, 'source_tasks': len(source),
               'source_candidate_labels': sum(row['n'] for row in source),
               'target_tasks': len(target), 'seed': SEED,
               'temperatures': TEMPERATURES, 'epochs': EPOCHS,
               'correct': {key: sum(row['correct'] for row in v['target'])
                           for key, v in variants.items()},
               'by_family': {key: {family: sum(row['correct'] for row in v['target']
                                               if row['family'] == family)
                                   for family in families}
                             for key, v in variants.items()},
               'source_correct': {key: sum(row['correct'] for row in v['source'])
                                  for key, v in variants.items()},
               'wall_seconds': time.perf_counter() - start}
    write_json(OUT, {'summary': summary, 'normalization_mean': mean.tolist(),
                     'normalization_scale': scale.tolist(), 'variants': variants})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
