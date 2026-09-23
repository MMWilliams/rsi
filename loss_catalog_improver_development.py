"""Source-cross-validated improver decision over evaluator loss edits."""
from __future__ import annotations

import hashlib
import json
import time

import numpy as np
import torch

from rsi.common import ROOT, write_json
from listwise_evaluator_development import pack
from temperature_ranker_development import train, score, TEMPERATURES


SOURCE = ROOT / 'analysis/mixed-evaluator-source.json'
OUT = ROOT / 'analysis/loss-catalog-improver-development.json'
FOLDS = 2


def fold(row):
    return int.from_bytes(hashlib.sha256(row['id'].encode()).digest()[:8], 'little') % FOLDS


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    rows = json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    start = time.perf_counter()
    validation = {str(temperature): [] for temperature in TEMPERATURES}
    by_fold = []
    for heldout in range(FOLDS):
        training = [row for row in rows if fold(row) != heldout]
        testing = [row for row in rows if fold(row) == heldout]
        x, _, _ = pack(training)
        mean = x.mean(axis=0)
        scale = np.maximum(x.std(axis=0), .05)
        fold_score = {}
        for temperature in TEMPERATURES:
            model, _ = train(temperature, training, mean, scale, device)
            correct = score(model, mean, scale, testing, device)
            validation[str(temperature)].extend(correct)
            fold_score[str(temperature)] = sum(row['correct'] for row in correct)
        by_fold.append({'fold': heldout, 'training_tasks': len(training),
                        'validation_tasks': len(testing), 'correct': fold_score})
    aggregate = {key: sum(row['correct'] for row in value)
                 for key, value in validation.items()}
    chosen = max(TEMPERATURES, key=lambda t: (aggregate[str(t)], -t))
    summary = {'scope': 'development only; source whole-task cross-validation',
               'device': device, 'source_tasks': len(rows),
               'source_candidate_labels': sum(row['n'] for row in rows),
               'folds': FOLDS, 'training_fits': FOLDS * len(TEMPERATURES),
               'epochs_per_fit': 120, 'validation_correct': aggregate,
               'selected_temperature': chosen,
               'wall_seconds': time.perf_counter() - start}
    write_json(OUT, {'summary': summary, 'by_fold': by_fold,
                     'validation': validation})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
