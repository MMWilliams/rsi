"""Fresh v2 banks; arithmetic constants stay host-owned."""
import random
from rsi.common import digest
from seed_casebanks import random_bank


def changed_bank(seed=207006,count=12):
    rng=random.Random(seed); tasks=[]
    rules=((4,11,3,8,1),(8,5,7,6,2),(7,2,9,5,3),(2,7,5,9,5))
    for index in range(count):
        mul,add,div,mod,res=rules[index%len(rules)]
        alphabet=[chr(0x800+i) for i in range(256)]
        positive=[c for c in alphabet if ((ord(c)*mul+add)//div)%mod==res]
        negative=[c for c in alphabet if c not in positive]
        direction=rng.choice((True,False)); before=rng.choice((True,False))
        left,right=(positive,negative) if direction else (negative,positive)
        pairs=[]
        for _ in range(24):
            a=''.join(rng.choice(left) for _ in range(rng.randint(2,5)))
            b=''.join(rng.choice(right) for _ in range(rng.randint(2,5)))
            pairs.append([a+b,a if before else b])
        tasks.append({'id':digest([seed,index,pairs])[:24],'family':'shifted_ast_v2',
            'reference':{'rule':rules[index%len(rules)],'direction':direction,'before':before},
            'visible':pairs[:8],'hidden':pairs[8:]})
    return tasks


def generate():
    return {'bootstrap':random_bank(207001,6),'reservoir':random_bank(207002,48),
        'admission':random_bank(207003,36),'final_mixed':random_bank(207004,24),
        'final_ast':random_bank(207005,12,('ast_transition',)),'final_changed':changed_bank()}
