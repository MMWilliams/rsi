"""Information-boundary and admission regression tests for the new seed study."""
import numpy as np
from seed_casebanks import random_bank
from seed_growth import representation
from seed_source_search import gate_allowed
from rsi.common import digest


def test_public_examples_are_randomized_and_separate():
    banks=[random_bank(seed,12) for seed in (205801,205802)]
    visible=[digest(t['visible']) for bank in banks for t in bank]
    assert len(set(visible))==len(visible)
    for bank in banks:
        for task in bank:
            assert len(task['visible'])==8 and len(task['hidden'])==16
            assert not set(map(tuple,task['visible'])) & set(map(tuple,task['hidden']))


def test_features_ignore_oracle_metadata():
    task=random_bank(205803,1)[0]
    row={'program':'Concat()','source':'v67'}
    first=representation({'id':task['id'],'visible':task['visible']},[row])
    poisoned=representation({**task,'hidden':[['secret','wrong']],'reference':'poison'},
                            [{**row,'oracle_correct':True,'family':'secret'}])
    for key in ('lexical','structural','behavior','boundary','context'):
        assert np.array_equal(first[key],poisoned[key])


def test_gate_retains_ties_and_blocks_group_regression():
    old={'correct':1,'rows':[{'block':1,'correct':True},{'block':2,'correct':False},{'block':2,'correct':False}]}
    new={'correct':2,'rows':[{'block':1,'correct':False},{'block':2,'correct':True},{'block':2,'correct':True}]}
    assert not gate_allowed(old,old,'strict')
    assert gate_allowed(old,new,'strict')
    assert not gate_allowed(old,new,'retention')
