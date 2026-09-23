"""Random public examples plus distinct, host-owned oracle examples."""
import random
from rsi.common import digest
from rsi.evolving_domain import make_task

FAMILIES=('transform_transition','ast_transition','novel_operator_transition',
          'stack_transition','mutation_transition','self_edit_transition')


def random_bank(seed,count,families=FAMILIES,visible=8,hidden=16):
    rng=random.Random(seed); tasks=[]
    for index in range(count):
        family=families[index%len(families)]
        task=make_task(rng,'random_public',index,family,0,visible+hidden)
        examples=task['hidden']
        task.update({'visible':examples[:visible],'hidden':examples[visible:],'family':family,
                     'id':digest([seed,index,family,examples])[:24]})
        tasks.append(task)
    return tasks


def shifted_ast_bank(seed,count,visible=8,hidden=16):
    """New supported arithmetic mechanisms, never labels derived from candidates."""
    rng=random.Random(seed); tasks=[]
    rules=((7,11,6,5,1),(2,13,7,9,4),(5,1,3,7,2),(9,7,8,5,3))
    for index in range(count):
        multiplier,addend,divisor,modulus,residue=rules[index%len(rules)]
        def special(char): return ((ord(char)*multiplier+addend)//divisor)%modulus==residue
        alphabet=[chr(0x800+i) for i in range(256)]
        positive=[c for c in alphabet if special(c)]; negative=[c for c in alphabet if not special(c)]
        direction=rng.choice((True,False)); before=rng.choice((True,False))
        left,right=(positive,negative) if direction else (negative,positive)
        examples=[]
        for _ in range(visible+hidden):
            a=''.join(rng.choice(left) for _ in range(rng.randint(2,5)))
            b=''.join(rng.choice(right) for _ in range(rng.randint(2,5)))
            examples.append([a+b,a if before else b])
        tasks.append({'id':digest([seed,index,examples])[:24],'family':'shifted_ast',
            'reference':{'parameters':rules[index%len(rules)],'direction':direction,'before':before},
            'visible':examples[:visible],'hidden':examples[visible:]})
    return tasks
