"""Prespecified colder-start episodes with new held-out arithmetic parameters."""
import random

from rsi.common import digest
from seed_casebanks import random_bank


RULES = ((11,3,4,7,2), (3,17,5,6,4), (13,9,7,11,6), (5,19,4,9,7))


def changed_bank(seed, count=12):
    rng = random.Random(seed)
    alphabet = [chr(0x800+i) for i in range(256)]
    tasks = []
    for index in range(count):
        mul, add, div, mod, residue = RULES[index % len(RULES)]
        positive = [c for c in alphabet if ((ord(c)*mul+add)//div)%mod == residue]
        negative = [c for c in alphabet if c not in positive]
        assert len(positive) > 5 and len(negative) > 5
        direction = rng.choice((True, False))
        before = rng.choice((True, False))
        left, right = (positive, negative) if direction else (negative, positive)
        pairs = []
        for _ in range(24):
            a = ''.join(rng.choice(left) for _ in range(rng.randint(2, 5)))
            b = ''.join(rng.choice(right) for _ in range(rng.randint(2, 5)))
            pairs.append([a+b, a if before else b])
        tasks.append({'id': digest([seed,index,pairs])[:24], 'family':'shifted_ast_transfer',
                      'reference':{'rule':RULES[index%len(RULES)],'direction':direction,'before':before},
                      'visible':pairs[:8], 'hidden':pairs[8:]})
    return tasks


def banks(offset):
    assert offset in (3000,4000,5000,6000,7000,8000)
    return {'bootstrap':random_bank(207001+offset, 2),
            'reservoir':random_bank(207002+offset, 48),
            'admission':random_bank(207003+offset, 36),
            'final_mixed':random_bank(207004+offset, 24),
            'final_ast':random_bank(207005+offset, 12, ('ast_transition',)),
            'final_changed':changed_bank(207006+offset, 12)}
