"""The frozen seed, recording the two states every proof compares, so that a
candidate the test rejected can still be scored afterwards. Seed.prove runs
unchanged, so a recorded run is the full arm's run.
"""
from __future__ import annotations

import json

from .seed import Seed


def snap(state):
    areas = {name: {k: v for k, v in a.items() if k not in ('held_out_score', 'extension_score')}
             for name, a in state['areas'].items()}
    return {'version': state['version'], 'language': state['language'], 'areas': areas, 'inventions': state['inventions']}


class Recording(Seed):
    def prove(self, area, held_out, salt, candidate, budget, change, **options):
        folder = self.path / 'candidates'
        folder.mkdir(exist_ok=True)
        k = sum(e['op'] == 'prove' for e in self.state['ledger'])   # this proof's index among the ledger's proofs
        (folder / f'{k}.json').write_text(json.dumps({
            'area': area.name, 'change': change, 'experience_len': len(self.state['experience']),
            'carried': snap(self.state), 'candidate': snap(candidate)}))
        return super().prove(area, held_out, salt, candidate, budget, change, **options)
