"""The second draw's summary: a paired difference is called ahead or behind only
when its interval over resampled worlds excludes zero."""
import json

import second_draw
from summarize_arms import AREAS, TAGS


def test_verdicts_follow_the_paired_interval(tmp_path, monkeypatch):
    worlds = 8
    level = {'start': 10, 'open': 15, 'full': 20, 'matched': 25, 'no-guidance': 12}   # every other arm equals full
    hits = {f'{label}/{tag}/{area}': [level.get(label, 20) + (i % 3) for i in range(worlds)]
            for label in second_draw.ARMS + ('start', 'open') for tag in TAGS for area in AREAS}
    pools = {f'{tag}/{area}': ['a', 'b'] * (worlds // 2) for tag in TAGS for area in AREAS}
    monkeypatch.setattr(second_draw, 'HITS', tmp_path / 'hits.json')
    monkeypatch.setattr(second_draw, 'OUT', tmp_path / 'out.json')
    monkeypatch.setattr(second_draw, 'DRAWS', 400)
    second_draw.HITS.write_text(json.dumps({'salt': second_draw.SALT, 'per_pool': worlds // 2, 'pools': pools, 'hits': hits}))
    second_draw.summarize()
    out = json.loads(second_draw.OUT.read_text())
    assert out['arms']['matched']['verdicts'] == ['ahead'] * len(TAGS)
    assert out['arms']['no-guidance']['verdicts'] == ['behind'] * len(TAGS)
    assert out['arms']['point']['verdicts'] == ['tie'] * len(TAGS)
    run = out['runs'][TAGS[0]]
    assert run['matched']['G_minus_full'] > 0 > run['no-guidance']['G_minus_full']
    assert run['open']['G_full_minus_open'] > 0 and all(v > 1 for v in run['open']['full_over_open'].values())
