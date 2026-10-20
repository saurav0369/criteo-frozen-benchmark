import csv, tempfile
from pathlib import Path
from c021_strong_context import evaluate,fullidx,SparseFTRL,SparseSGD
from c021_strong_context import N_BUCKETS

a={'campaign':'a',**{f'cat{i}':str(i) for i in range(1,10)}}
x=fullidx(a)
assert len(set(x))>=8
for Model in [SparseFTRL,SparseSGD]:
    m=Model();p=m.estimate(tuple(range(10)))
    for _ in range(100):m.learn(tuple(range(10)),1)
    assert m.estimate(tuple(range(10)))>p
with tempfile.TemporaryDirectory() as td:
    d=Path(td)
    cols=['timestamp','campaign','conversion','conversion_timestamp',*[f'cat{i}' for i in range(1,10)]]
    rows=[]
    for i in range(1400):
        t=i*2000;y=int(i%37==0)
        row={'timestamp':t,'campaign':str(i%20),'conversion':y,
             'conversion_timestamp':t+10000 if y else -1}
        row.update({f'cat{k}':str((i*k)%17) for k in range(1,10)})
        rows.append(row)
    a=d/'demo.tsv'
    with a.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter='\t');w.writeheader();w.writerows(rows)
    res=evaluate(a,sample_every=1)
    assert res['dev_examples']>0 and res['holdout_outcomes_evaluated']==0
    for row in rows:
        if row['timestamp']>=res['development_time_boundary']:
            row['conversion']=1-row['conversion']
            row['conversion_timestamp']=row['timestamp']+10000 if row['conversion'] else -1
    b=d/'poison.tsv'
    with b.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter='\t');w.writeheader();w.writerows(rows)
    poisoned=evaluate(b,sample_every=1)
    assert res['metrics']==poisoned['metrics']
    assert res['baseline_prediction_digest']==poisoned['baseline_prediction_digest']
    assert res['paired_block_uncertainty']==poisoned['paired_block_uncertainty']
    print('PASS full-feature input, positive-learning, chronological labels and holdout-poison invariance')
