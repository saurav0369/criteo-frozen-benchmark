#!/usr/bin/env python3
"""Cycle 018: frozen *additional* prequential baselines for Criteo attribution dataset.

No real metrics may be reported without the official TSV. Real data's recorded conversion
event time is an availability PROXY, not a historical ingestion/publishing timestamp.

The last 30% of impression clock-time is never parsed for labels. Original C017
algorithm and result are not modified. This is an E2 synthetic preflight until data arrives.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, heapq, json, math
from collections import defaultdict, deque
from array import array
from pathlib import Path

DAY=86400
HORIZON=7*DAY
ALLOW=('campaign','cat1','cat2')
NEEDED=('timestamp','campaign','conversion','conversion_timestamp','cat1','cat2')
FIXED_P=0.005 # hypothetical public, predeclared prior, NOT derived from held-out labels
PRIOR_WEIGHT=200.0 # Beta pseudo-counts, 0.005 mean; fair prior for all count models
CAMPAIGN_WEIGHT=50.0
ROLL=7*DAY
HASH_CAP=1<<16
STEP_SIZE=0.05
B0=math.log(FIXED_P/(1-FIXED_P))


def opened(path):
    return gzip.open(path,'rt',newline='',encoding='utf-8') if str(path).endswith('.gz') else open(path,'rt',newline='',encoding='utf-8')


def time_scan(path):
    n=0;lo=hi=None
    with opened(path) as f:
        header=f.readline().strip().split('\t')
        if not header or header[0]!='timestamp': raise ValueError('Expected timestamp at column 0')
        if len(header)!=len(set(header)):raise ValueError('Repeated column names')
        for line in f:
            if not line.strip():continue
            t=int(line.split('\t',1)[0]);n+=1
            if hi is not None and t<hi:raise ValueError('Data not sorted by timestamp')
            if lo is None:lo=t
            hi=t
    if n<1000 or hi<=lo:raise ValueError('Insufficient timestamps')
    return lo,hi,n


def released(row):
    t=int(row['timestamp']); conv=int(row['conversion']);tc=int(row['conversion_timestamp'])
    if conv==0:
        if tc!=-1:raise ValueError('Nonconverter must have conversion_timestamp=-1')
        return 0,t+HORIZON
    if conv!=1 or tc<t or tc>t+30*DAY:raise ValueError('Invalid conversion timestamp or flag')
    if tc>t+HORIZON:return 0,t+HORIZON
    return 1,tc


def features(row):
    # feature identity is from the impression-time context only; no future fields.
    raw=('campaign='+row['campaign'],'cat1='+row['cat1'],'cat2='+row['cat2'])
    idx=[]
    for x in raw:
        h=int.from_bytes(hashlib.blake2b(x.encode('utf-8'),digest_size=8).digest(),'little')
        idx.append(h%HASH_CAP)
    return tuple(idx)


def prob(z):
    z=max(-30.,min(30.,z))
    return 1/(1+math.exp(-z))


class HashedLogit:
    def __init__(self):
        self.weights=array('d',[0.0])*HASH_CAP
        self.bias=B0
        self.received=0
    def estimate(self,idx):
        return prob(self.bias+sum(self.weights[i] for i in idx))
    def learn(self,idx,y):
        p=self.estimate(idx)
        # fixed online gradient update; no hyperparameter tuning on development labels
        delta=STEP_SIZE*(y-p)
        self.bias+=delta
        for i in idx:self.weights[i]+=delta
        self.received+=1


class StreamModels:
    def __init__(self):
        self.heap=[];self.hist=deque();self.hist_sum=0
        self.global_n=0;self.global_y=0;self.camps=defaultdict(lambda:[0,0]);self.recv=0
        self.mature_heap=[];self.mature_n=0;self.mature_y=0
        self.mature_camps=defaultdict(lambda:[0,0]);self.mature_recv=0
        self.logit_early=HashedLogit();self.logit_mature=HashedLogit();self.previous_t=-1
    def flush(self,t):
        if t<self.previous_t:raise AssertionError('Time reversal')
        self.previous_t=t
        while self.heap and self.heap[0][0]<=t:
            rt,i,y,camp,idx=heapq.heappop(self.heap)
            self.global_n+=1;self.global_y+=y
            v=self.camps[camp];v[0]+=y;v[1]+=1
            self.hist.append((rt,y));self.hist_sum+=y
            self.logit_early.learn(idx,y);self.recv+=1
        while self.hist and self.hist[0][0]<t-ROLL:
            rt,y=self.hist.popleft();self.hist_sum-=y
        while self.mature_heap and self.mature_heap[0][0]<=t:
            rt,i,y,camp,idx=heapq.heappop(self.mature_heap)
            self.mature_n+=1;self.mature_y+=y
            v=self.mature_camps[camp];v[0]+=y;v[1]+=1
            self.logit_mature.learn(idx,y);self.mature_recv+=1
    def estimates(self,camp,idx):
        ep=(self.global_y+FIXED_P*PRIOR_WEIGHT)/(self.global_n+PRIOR_WEIGHT)
        mp=(self.mature_y+FIXED_P*PRIOR_WEIGHT)/(self.mature_n+PRIOR_WEIGHT)
        ey,en=self.camps[camp]
        my,mn=self.mature_camps[camp]
        rolling=(self.hist_sum+FIXED_P*PRIOR_WEIGHT)/(len(self.hist)+PRIOR_WEIGHT)
        return {'fixed_prior':FIXED_P,'global_event':ep,'rolling_event':rolling,
                'campaign_event':(ey+ep*CAMPAIGN_WEIGHT)/(en+CAMPAIGN_WEIGHT),
                'global_mature':mp,
                'campaign_mature':(my+mp*CAMPAIGN_WEIGHT)/(mn+CAMPAIGN_WEIGHT),
                'hashed_logit_event':self.logit_early.estimate(idx),
                'hashed_logit_mature':self.logit_mature.estimate(idx)}
    def enqueue(self,i,impression_time,release_time,camp,idx,y):
        if release_time<self.previous_t or impression_time!=self.previous_t:
            raise AssertionError('Invalid schedule')
        heapq.heappush(self.heap,(release_time,i,y,camp,idx))
        heapq.heappush(self.mature_heap,(impression_time+HORIZON,i,y,camp,idx))


def hash_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while True:
            b=f.read(4*1024*1024)
            if not b:break
            h.update(b)
    return h.hexdigest()

def evaluate(path,sample_every=10):
    if sample_every<1:raise ValueError('sample_every must be positive')
    lo,hi,rows=time_scan(path)
    warm=lo+.30*(hi-lo);devend=lo+.70*(hi-lo)
    eng=StreamModels();loss=defaultdict(float);brier=defaultdict(float)
    num=0;warm_num=0;n_sample=0;hasher=hashlib.sha256()
    with opened(path) as f:
        dr=csv.DictReader(f,delimiter='\t')
        if not set(NEEDED).issubset(dr.fieldnames):raise ValueError('Missing required column')
        for i,row in enumerate(dr):
            t=int(row['timestamp'])
            if t>=devend:break # HOLDOUT: never touch label or any other feature.
            if i%sample_every:continue
            n_sample+=1
            eng.flush(t)
            camp=row['campaign'];idx=features(row)
            ps=eng.estimates(camp,idx)
            # Scoring is permitted on development labels, but never before predictions.
            y,releasetime=released(row)
            if t>=warm:
                for method,p in ps.items():
                    p=min(1-1e-12,max(1e-12,p))
                    loss[method]-=y*math.log(p)+(1-y)*math.log1p(-p)
                    brier[method]+=(y-p)**2
                hasher.update((str(i)+';'+','.join(f'{ps[m]:.12g}' for m in sorted(ps))+'\n').encode())
                num+=1
            else:warm_num+=1
            eng.enqueue(i,t,releasetime,camp,idx,y)
    if num==0:raise ValueError('No development prediction rows')
    return {'status':'SYNTHETIC_ONLY unless official source externally verified','src':str(path),
            'src_rows':rows,'first_t':lo,'last_t':hi,
            'warmup_boundary':warm,'development_end':devend,'source_hash':hash_file(path),
            'sample_every':sample_every,'sampled_preholdout':n_sample,'warmup_samples':warm_num,'dev_predictions':num,
            'event_labels_received':eng.recv,'fully_matured_labels_received':eng.mature_recv,
            'holdout_outcomes_evaluated':0,'prediction_digest':hasher.hexdigest(),
            'event_timestamps_are_not_publication_timestamps':True,
            'params':{'prior':FIXED_P,'prior_weight':PRIOR_WEIGHT,'campaign_weight':CAMPAIGN_WEIGHT,
                      'hash_features':list(ALLOW),'hash_size':HASH_CAP,'logit_step_size':STEP_SIZE},
            'metrics':{m:{'logloss':round(loss[m]/num,9),'brier':round(brier[m]/num,9)} for m in sorted(loss)}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--sample-every',type=int,default=10)
    a=p.parse_args();result=evaluate(Path(a.input),a.sample_every)
    Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'dev_predictions':result['dev_predictions'],'metrics':result['metrics'],'heldout_outcomes_evaluated':0},indent=2))
if __name__=='__main__':main()
