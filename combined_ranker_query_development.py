"""Opened-bank CV of E0/E1 rankers with matched cheap query learners."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json
from candidate_query_cost_transfer import cheap_public_features
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


PANELS=(ROOT/'runs/candidate-reranker-transfer-20260918',
        ROOT/'runs/candidate-reranker-replication-20260918',
        ROOT/'runs/candidate-conditioned-query-transfer-20260918',
        ROOT/'runs/candidate-query-cost-transfer-20260918')
OUT=ROOT/'analysis/combined-ranker-query-development-20260918.json'
RANKERS=('e0','e1')


def feature_for(record,matrix,ranker):
    if ranker=='e0':return cheap_public_features(record,matrix)
    replacement={**record,'orders':{**record['orders'],
                                    'e0':record['orders'][ranker]}}
    return cheap_public_features(replacement,matrix)


def source_rows():
    result=[]
    for panel in PANELS:
        assert json.loads((panel/'audit.json').read_text())['passed']
        records=json.loads((panel/'frozen_records.json').read_text())
        matrix=json.loads((panel/'predicted_probe_outputs.json').read_text())
        outcomes=json.loads((panel/'results.json').read_text())['tasks']
        for record,outcome in zip(records,outcomes):
            assert record['id']==outcome['id']
            row={'id':record['id'],'seed':record['seed'],
                 'family':record['family'],'public_block':record['public_block']}
            for name in RANKERS:
                row[name]={'features':feature_for(record,matrix[record['id']],name),
                           'zero':outcome['zero'][name],
                           'one':outcome['one'][name],
                           'gain':outcome['one'][name]-outcome['zero'][name]}
            result.append(row)
    assert len(result)==2304 and len({r['id'] for r in result})==2304
    return result


def model_rows(rows,name):
    return [{'id':r['id'],'seed':r['seed'],'public_block':r['public_block'],
             **r[name]} for r in rows]


def score_bank(rows,name,predictions):
    order=sorted(range(len(rows)),key=lambda i:(float(predictions[i]),rows[i]['id']),
                 reverse=True)
    selected={rows[i]['id'] for i in order[:8]}
    return sum(r[name]['one'] if r['id'] in selected else r[name]['zero'] for r in rows)


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows=source_rows();seeds=sorted({r['seed'] for r in rows})
    assert len(seeds)==48
    banks=[]
    for seed in seeds:
        source=[r for r in rows if r['seed']!=seed]
        target=[r for r in rows if r['seed']==seed]
        entry={'seed':seed}
        for name in RANKERS:
            model=fit_method(model_rows(source,name),'interaction_100')
            p=values(model,model_rows(target,name))
            entry[name]=score_bank(target,name,p)
            entry[f'{name}_noquery']=sum(r[name]['zero'] for r in target)
        banks.append(entry)
    totals={name:sum(r[name] for r in banks) for name in
            ('e0','e1','e0_noquery','e1_noquery')}
    diffs=[r['e1']-r['e0'] for r in banks]
    result={'scope':'opened 48-bank cross-validation, no fresh package claim',
        'tasks':len(rows),'banks':len(banks),'feature_count':24,
        'totals':totals,'e1_minus_e0':{'gain':sum(diffs),
            'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)},
        'by_bank':banks}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='by_bank'},indent=2))


if __name__=='__main__':main()
