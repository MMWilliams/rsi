import numpy as np
import seed_integrated_v2 as v2


def record(name,n):
    return {'id':name,'public':{'id':name,'visible':[]},
        'rows':[{'program':'p'+str(i),'source':'v67'} for i in range(n)],
        'features':{'lexical':np.zeros((n,10)),'structural':np.zeros((n,175)),
                    'behavior':np.zeros((n,256)),'boundary':np.zeros(n),'context':np.zeros(37),'block':0}}


def test_exact_label_budget_with_partial_task(monkeypatch):
    originals=[record('a',5),record('b',3)]
    views=v2.remaining_views(originals,{})
    monkeypatch.setattr(v2,'acquire',lambda *args,**kwargs:[{'id':r['id'],'score':0.} for r in views])
    opened=[]
    def oracle(key,indices):
        opened.extend((key,i) for i in indices)
        return [int(i%2==0) for i in indices]
    purchased={}
    v2.purchase({},views,'novelty',oracle,purchased,allowance=6)
    assert opened==[('a',i) for i in range(5)]+[('b',0)]
    remaining=v2.remaining_views(originals,purchased)
    assert len(remaining)==1 and remaining[0]['candidate_indices']==[1,2]
    known=v2.train_records([],originals,purchased)
    assert sum(len(r['labels']) for r in known)==6
    assert remaining[0]['id']!=known[1]['id']


def test_admission_and_prediction_use_same_policy(monkeypatch):
    r=record('a',2)
    monkeypatch.setattr(v2,'predict',lambda model,rec:{'ensemble':np.array([.50,.52])})
    monkeypatch.setattr(v2,'base_index',lambda rows:0)
    for policy,expected in [('argmax',1),('margin',0)]:
        pred=v2.predictions({},[r],policy)['a']
        admitted=v2.admission({},[r],lambda key:[0,1],policy)
        assert pred['deployed']==admitted['rows'][0]['index']==expected
        assert admitted['correct']==expected


def test_proper_tie_requires_retention_and_real_error_gain():
    old={'correct':1,'brier':.2,'rows':[{'block':1,'correct':True},{'block':2,'correct':False}]}
    new={**old,'brier':.198}
    assert v2.accept(old,new,'proper_tie')
    assert not v2.accept(old,new,'strict')
    assert not v2.accept(old,{**old,'brier':.1999},'proper_tie')
    bad={'correct':1,'brier':.1,'rows':[{'block':1,'correct':False},{'block':2,'correct':True}]}
    assert not v2.accept(old,bad,'proper_tie')
