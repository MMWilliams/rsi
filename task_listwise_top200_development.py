"""Opened-bank matched-label screen of candidate BCE and task-listwise AST rankers."""
from __future__ import annotations

import json

import joblib
import numpy as np
import torch

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from dual_specialist_seed_evaluator import load_models
from wide_candidate_reranker_development import features
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from candidate_stacking_development import SOURCE, ADDED


TARGET = ROOT / 'runs/candidate-stacking-feedback-transfer-20260918'
OUT = ROOT / 'analysis/task-listwise-top200-development-20260918.json'
MODELS = ROOT / 'analysis/task-listwise-top200-models-20260918'
WIDTH = 200
DIM = 191
EPOCHS = 120
TEMPERATURE = .25
SEED = 905200


class Ranker(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = torch.nn.Sequential(torch.nn.Linear(DIM, 32),
                                           torch.nn.ReLU(),
                                           torch.nn.Linear(32, 1))

    def forward(self, x):
        return self.layers(x).squeeze(-1)


def panel(path, specialists):
    tasks = json.loads((path / 'sealed_bank.json').read_text())
    base = json.loads((path / 'base_pools.json').read_text())
    wide = json.loads((path / 'ast_wide_pools.json').read_text())
    records = json.loads((path / 'frozen_records.json').read_text())
    rows = []
    for task, rec in zip(tasks, records):
        pool = wide.get(task['id'], base[task['id']])
        old = rec['orders']['old']
        n = min(WIDTH, len(old))
        structural = features(task, pool, rec, n)
        pf = specialists['familiar'].predict_proba(structural)[:, 1]
        ps = specialists['shifted'].predict_proba(structural)[:, 1]
        score = np.asarray(rec['old_scores'], float)
        std = max(float(score.std()), .05)
        meta = np.stack((pf, ps, np.maximum(pf, ps),
                         np.abs(pf - ps), pf*ps,
                         (score[old[:n]] - score[old[0]])/std,
                         np.arange(n)/100.), axis=1).astype(np.float32)
        x = np.c_[structural, meta].astype(np.float32)
        y = np.asarray([int(bool(evaluate_program(pool[i]['program'],
                                                   task['hidden'][8:])))
                        for i in old[:n]], np.int8)
        rows.append({'id': task['id'], 'seed': task['seed'],
                     'domain': 'shifted' if task['family'] == 'shifted_ast'
                     else 'familiar', 'x': x, 'y': y,
                     'pf': pf, 'ps': ps})
    return rows


def packed(rows):
    x = np.concatenate([r['x'] for r in rows])
    y = np.concatenate([r['y'] for r in rows])
    return x, y


def fit_listwise(rows, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    x, _ = packed(rows)
    mean = x.mean(axis=0).astype(np.float32)
    scale = np.maximum(x.std(axis=0), .05).astype(np.float32)
    tx = np.zeros((len(rows), WIDTH, DIM), np.float32)
    valid = np.zeros((len(rows), WIDTH), bool)
    positive = np.zeros((len(rows), WIDTH), bool)
    for i, row in enumerate(rows):
        n = len(row['y'])
        tx[i, :n] = (row['x']-mean)/scale
        valid[i, :n] = True
        positive[i, :n] = row['y'].astype(bool)
    active = positive.any(axis=1) & ~(positive == valid).all(axis=1)
    assert active.any()
    xgpu = torch.from_numpy(tx).to(device)
    vgpu = torch.from_numpy(valid).to(device)
    pgpu = torch.from_numpy(positive).to(device)
    agpu = torch.from_numpy(active).to(device)
    model = Ranker().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001,
                                   weight_decay=.001)
    checkpoints = {}
    for epoch in range(1, EPOCHS+1):
        model.train()
        optimizer.zero_grad()
        logits = model(xgpu)/TEMPERATURE
        all_score = torch.logsumexp(logits.masked_fill(~vgpu, -1e9), dim=1)
        good_score = torch.logsumexp(logits.masked_fill(~pgpu, -1e9), dim=1)
        loss = (all_score-good_score)[agpu].mean()
        loss.backward()
        optimizer.step()
        if epoch in (40, 80, EPOCHS):
            checkpoints[str(epoch)] = {
                key: value.detach().cpu().numpy().copy()
                for key, value in model.state_dict().items()}
    return {'mean': mean, 'scale': scale, 'weights': checkpoints,
            'active_tasks': int(active.sum()), 'training_loss': float(loss),
            'device': device}


def predict_listwise(frozen, x, epoch='120'):
    model = Ranker()
    model.load_state_dict({key: torch.from_numpy(value)
                           for key, value in frozen['weights'][epoch].items()})
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy((x-frozen['mean']) /
                                      frozen['scale'])).numpy()


def evaluate(rows, models):
    banks = []
    score_rows = []
    for row in rows:
        x, y = row['x'], row['y']
        pf, ps = row['pf'], row['ps']
        familiar = int(np.argmax(pf))
        shifted = int(np.argmax(ps))
        dual = shifted if ps[shifted] > pf[familiar] else familiar
        picks = {'dual200': dual,
                 'candidate_mean200': int(np.argmax((pf+ps)/2))}
        for name, model in models.items():
            p = (predict_listwise(model, x) if isinstance(model, dict)
                 else model.predict_proba(x)[:, 1])
            picks[name] = int(np.argmax(p))
        score_rows.append({'seed': row['seed'], 'domain': row['domain'],
                           'reachable': int(bool(y.any())),
                           'labels': {name: int(y[index]) for name, index
                                      in picks.items()}})
    names = score_rows[0]['labels']
    for seed in sorted({r['seed'] for r in rows}):
        group = [r for r in score_rows if r['seed'] == seed]
        banks.append({'seed': seed,
                      'reachable': sum(r['reachable'] for r in group),
                      **{name: sum(r['labels'][name] for r in group)
                         for name in names}})
    totals = {key: sum(b[key] for b in banks) for key in banks[0]
              if key != 'seed'}
    comparisons = {}
    for name in names:
        if name == 'dual200':
            continue
        d = [b[name]-b['dual200'] for b in banks]
        comparisons[name+'_minus_dual'] = {'gain': sum(d),
            'positive_banks': sum(v>0 for v in d),
            'negative_banks': sum(v<0 for v in d),
            'interval': interval(d)}
    return {'tasks': len(rows), 'totals': totals,
            'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    paths = SOURCE+(ADDED,TARGET)
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in paths)
    specialists = load_models()
    panels = [panel(path, specialists) for path in paths]
    early = panels[0]+panels[1]
    later = early+panels[2]
    rng = np.random.default_rng(SEED+1)
    scrambled = []
    for row in panels[2]:
        scrambled.append({**row, 'y': rng.permutation(row['y'])})
    duplicate = [early[i] for i in rng.choice(len(early), len(panels[2]),
                                               replace=True)]
    trained = {}
    for name, rows in (('early_listwise', early),
                       ('later_listwise', later),
                       ('scrambled_listwise', early+scrambled),
                       ('duplicate_listwise', early+duplicate)):
        trained[name] = fit_listwise(rows, SEED)
        print(name, 'trained', flush=True)
    for name, rows in (('early_bce', early), ('later_bce', later)):
        x, y = packed(rows)
        trained[name] = model_for(15).fit(x,y)
        print(name, 'trained', flush=True)
    MODELS.mkdir(parents=True)
    for name, model in trained.items():
        joblib.dump(model, MODELS/f'{name}.joblib', compress=3)
    targets = {path.name: evaluate(rows, trained)
               for path, rows in zip(paths[2:], panels[2:])}
    result = {'scope': 'opened development only',
              'config': {'width': WIDTH, 'features': DIM,
                         'listwise_temperature': TEMPERATURE,
                         'epochs': EPOCHS, 'seed': SEED},
              'source': {'early_tasks': len(early), 'later_tasks': len(later),
                         'early_candidate_labels': sum(len(r['y']) for r in early),
                         'later_candidate_labels': sum(len(r['y']) for r in later)},
              'targets': targets,
              'training': {name: {'active_tasks': model['active_tasks'],
                                 'training_loss': model['training_loss'],
                                 'device': model['device']}
                           for name, model in trained.items()
                           if isinstance(model, dict)}}
    write_json(OUT, result)
    print(json.dumps({'scope': result['scope'], 'config': result['config'],
                      'source': result['source'], 'training': result['training'],
                      'targets': {key: {k:v for k,v in val.items() if k!='banks'}
                                  for key,val in targets.items()}}, indent=2))


if __name__ == '__main__':
    main()
