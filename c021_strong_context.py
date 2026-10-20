#!/usr/bin/env python3
"""Exploratory C021: frozen C018 parity plus stronger conventional sparse models.
Do not score the reserved holdout. Do not describe as confirmatory/SOTA.
"""
from __future__ import annotations
import argparse, csv, hashlib, heapq, json, math, random
from array import array
from collections import defaultdict
from pathlib import Path
import c018_runner as old

SRC_SHA='94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98'
REFERENCE_DIGEST='b07ceeaffa7fdf9a633e8afda281580b68e7e47ba99c7d9f7f18a089f1adfc37'
REF_N=659718
REF_LOGLOSS={'hashed_logit_event':.118492401,'hashed_logit_mature':.118491600}
FULL=('campaign','cat1','cat2','cat3','cat4','cat5','cat6','cat7','cat8','cat9')
N_BUCKETS=1<<18
SEED=20261020
ALPHA=.1; BETA=1.; L1=1e-6; L2=1.
STEP=.05

def fullidx(row):
    return tuple(int.from_bytes(hashlib.blake2b((k+'='+row[k]).encode(),digest_size=8).digest(),'little')%N_BUCKETS for k in FULL)

class SparseSGD:
    def __init__(self):
        self.w=array('d',[0.])*N_BUCKETS
        self.bias=old.B0
        self.received=0
    def estimate(self,x):return old.prob(self.bias+sum(self.w[i] for i in x))
    def learn(self,x,y):
        p=self.estimate(x)
        delta=STEP*(y-p)
        self.bias+=delta
        for i in x:self.w[i]+=delta
        self.received+=1

class SparseFTRL:
    """Standard sparse FTRL-Proximal, with fixed prior-logit offset and a bias coordinate."""
    def __init__(self):
        self.z=array('d',[0.])*(N_BUCKETS+1)
        self.n=array('d',[0.])*(N_BUCKETS+1)
        self.received=0
    def weight(self,i):
        z=self.z[i]
        if abs(z)<=L1:return 0.
        return -(z-math.copysign(L1,z))/((BETA+math.sqrt(self.n[i]))/ALPHA+L2)
    def estimate(self,x):
        return old.prob(old.B0+self.weight(N_BUCKETS)+sum(self.weight(i) for i in x))
    def learn(self,x,y):
        x=(*x,N_BUCKETS)
        p=self.estimate(x)
        g=p-y
        for i in x:
            wi=self.weight(i)
            ni=self.n[i]
            ni2=ni+g*g
            sigma=(math.sqrt(ni2)-math.sqrt(ni))/ALPHA
            self.z[i]+=g-sigma*wi
            self.n[i]=ni2
        self.received+=1

class Extra:
    def __init__(self):
        self.model={
          'sgd_full_event':SparseSGD(), 'sgd_full_mature':SparseSGD(),
          'ftrl_full_event':SparseFTRL(), 'ftrl_full_mature':SparseFTRL()}
        self.early=[];self.mature=[]
        self.received_early=0;self.received_mature=0
    def flush(self,t):
        while self.early and self.early[0][0]<=t:
            _,i,y,idx=heapq.heappop(self.early)
            self.model['sgd_full_event'].learn(idx,y)
            self.model['ftrl_full_event'].learn(idx,y)
            self.received_early+=1
        while self.mature and self.mature[0][0]<=t:
            _,i,y,idx=heapq.heappop(self.mature)
            self.model['sgd_full_mature'].learn(idx,y)
            self.model['ftrl_full_mature'].learn(idx,y)
            self.received_mature+=1
    def estimates(self,x):return {k:v.estimate(x) for k,v in self.model.items()}
    def enqueue(self,i,t,rel,y,x):
        heapq.heappush(self.early,(rel,i,y,x))
        heapq.heappush(self.mature,(t+old.HORIZON,i,y,x))

def summarize_blocks(arr,baseline,competitor):
    vals=[];paired=[];valid=[]
    for b in arr:
        n=b.get('n',0)
        if n:
            d=(b['logloss'][competitor]-b['logloss'][baseline])/n
            paired.append(d);valid.append(b)
            vals.append({'start_offset_days':b['start_offset_days'],'rows':n,
                         'baseline':b['logloss'][baseline]/n,'candidate':b['logloss'][competitor]/n,
                         'paired_candidate_minus_baseline':d})
    rng=random.Random(SEED); boot=[]
    for i in range(10000):
        ix=[rng.randrange(len(valid)) for _ in range(len(valid))]
        denom=sum(valid[k]['n'] for k in ix)
        boot.append(sum(valid[k]['logloss'][competitor]-valid[k]['logloss'][baseline] for k in ix)/denom)
    boot.sort()
    return {'blocks':vals,'bootstrap_95pct_difference_logloss':[boot[249],boot[9749]],
            'bootstrap_blocks':len(valid),'bootstrap_replications':10000,
            'warning':'Exploratory moving chronology blocked into nonoverlapping 2-day buckets; few effective independent units, no iid inference.'}

def evaluate(path,sample_every=10,verify=False):
    lo,hi,n=old.time_scan(path)
    if verify and (n!=16468027 or old.hash_file(path)!=SRC_SHA):raise ValueError('Official source verification failed')
    warm=lo+.30*(hi-lo);devend=lo+.70*(hi-lo)
    base=old.StreamModels();extra=Extra()
    sums=defaultdict(float);brier=defaultdict(float);byblock={};num=0;hash0=hashlib.sha256()
    n_positive=0;bucket_sums=defaultdict(int)
    with old.opened(path) as f:
        rd=csv.DictReader(f,delimiter='\t')
        if not set((*old.NEEDED,*FULL)).issubset(rd.fieldnames):raise ValueError('Incomplete columns')
        for i,row in enumerate(rd):
            t=int(row['timestamp'])
            if t>=devend:break  # NEVER READ HOLDOUT LABELS
            if i%sample_every:continue
            base.flush(t);extra.flush(t)
            camp=row['campaign'];ix=old.features(row);x=fullidx(row)
            p0=base.estimates(camp,ix)
            p1=extra.estimates(x)
            y,rt=old.released(row)  # AFTER probabilities; only in warmup and development
            if t>=warm:
                num+=1;n_positive+=y
                key=int((t-warm)//(2*old.DAY))
                if key not in byblock:
                    byblock[key]={'n':0,'start_offset_days':2*key,'logloss':defaultdict(float),'brier':defaultdict(float)}
                b=byblock[key];b['n']+=1
                for m,p in {**p0,**p1}.items():
                    p=min(1-1e-12,max(1e-12,p));ll=-y*math.log(p)-(1-y)*math.log1p(-p);br=(y-p)**2
                    sums[m]+=ll;brier[m]+=br;b['logloss'][m]+=ll;b['brier'][m]+=br
                hash0.update((str(i)+';'+','.join(f'{p0[m]:.12g}' for m in sorted(p0))+'\n').encode())
            base.enqueue(i,t,rt,camp,ix,y)
            extra.enqueue(i,t,rt,y,x)
    if not num:raise ValueError('No development rows')
    scores={k:{'logloss':round(v/num,9),'brier':round(brier[k]/num,9)} for k,v in sums.items()}
    passed=(hash0.hexdigest()==REFERENCE_DIGEST and num==REF_N and
            all(abs(scores[k]['logloss']-v)<=.000000001 for k,v in REF_LOGLOSS.items()))
    if verify and not passed: raise AssertionError('Frozen reference parity FAILED')
    blocks=[byblock[k] for k in sorted(byblock)]
    pairs={a+'__vs__'+b:summarize_blocks(blocks,b,a) for a,b in [
        ('sgd_full_event','hashed_logit_event'),('sgd_full_mature','hashed_logit_mature'),
        ('ftrl_full_event','hashed_logit_event'),('ftrl_full_mature','hashed_logit_mature'),
        ('sgd_full_event','sgd_full_mature'),('ftrl_full_event','ftrl_full_mature')
    ]}
    return {'protocol':'C021-strong-context-v1.0/EXPLORATORY, no method tuning',
            'official_source_verified_before_run':bool(verify), 'source_rows':n,'source_sha256':SRC_SHA if verify else None,
            'warmup_time_boundary':warm,'development_time_boundary':devend,'dev_examples':num,'dev_positives':n_positive,
            'holdout_outcomes_evaluated':0,'sample_every':sample_every,'original_runner_sha256':'9cdd97e532428ec85c43b409d11eb7db689ff08147978a071edd7a30033b64ba',
            'baseline_prediction_digest':hash0.hexdigest(),'frozen_parity_pass':passed,
            'metric':'prequential 7-day conversion logloss primary; brier secondary',
            'baseline_mode':'frozen original C018 source unchanged',
            'additional_models':['sgd_full_event','sgd_full_mature','ftrl_full_event','ftrl_full_mature'],
            'params':{'categoricals':FULL,'hash_dim':N_BUCKETS,'stepsize_sgd':STEP,
                'ftrl':{'alpha':ALPHA,'beta':BETA,'l1':L1,'l2':L2},'bootstrap_seed':SEED},
            'metrics':scores,'chronological_blocks':[
              {'start_offset_days':b['start_offset_days'],'rows':b['n'],
               'logloss':{k:round(v/b['n'],9) for k,v in b['logloss'].items()},
               'brier':{k:round(v/b['n'],9) for k,v in b['brier'].items()}} for b in blocks],
            'paired_block_uncertainty':pairs,
            'limitations':['Observed event times are not verified publication times',
                           'C021 adds seven additional categorical inputs vs frozen C018, so the comparison confounds feature capacity and optimizer',
                           'Bootstrap over few time blocks is exploratory, not reliable significance',
                           'SGD/FTRL hyperparameters fixed without tuning and may not be optimal',
                           'Only one 30-day public dataset; no independent external replication']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--sample-every',type=int,default=10);ap.add_argument('--official',action='store_true');args=ap.parse_args()
    res=evaluate(Path(args.input),args.sample_every,args.official)
    Path(args.out).write_text(json.dumps(res,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'frozen_parity_pass':res['frozen_parity_pass'],'dev_examples':res['dev_examples'],
      'dev_positives':res['dev_positives'],'metrics':res['metrics'], 'holdout_outcomes_evaluated':0},indent=2))
if __name__=='__main__':main()
