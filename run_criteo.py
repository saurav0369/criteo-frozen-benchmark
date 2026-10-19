#!/usr/bin/env python3
"""Frozen G0 Criteo development-only delayed-feedback benchmark; no holdout scoring."""
import csv,gzip,hashlib,heapq,json,math,os,sys,urllib.request
from collections import defaultdict,deque
from pathlib import Path
URL="https://huggingface.co/datasets/criteo/criteo-attribution-dataset/resolve/main/criteo_attribution_dataset.tsv.gz"
SHA="94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98"
SIZE=653015824; DAY=86400; H=7*DAY
P=0.0028; SMOOTH=100.; CAMP=50.; LR=0.05; DIM=16384
KEYS=("timestamp","campaign","conversion","conversion_timestamp","cat1","cat2")
def download(p):
    if p.exists(): return
    req=urllib.request.Request(URL,headers={"User-Agent":"CriteoFrozenG0/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r,open(str(p)+".part","wb") as f:
        while True:
            x=r.read(2**20)
            if not x:break
            f.write(x)
    os.replace(str(p)+".part",p)
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(2**20),b""):h.update(block)
    return h.hexdigest()
def rows(p):
    with gzip.open(p,"rt",encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f,delimiter="\t")
        if not set(KEYS).issubset(reader.fieldnames):raise ValueError("Missing columns")
        yield from reader
def scan(p):
    n=0;lo=hi=None;prev=None
    for r in rows(p):
        t=int(r["timestamp"])
        if prev is not None and t<prev:raise ValueError("Input not ordered chronologically")
        if lo is None:lo=t
        hi=t;prev=t;n+=1
    return n,lo,hi
def label(r,t):
    y=int(r["conversion"])
    ct=int(r["conversion_timestamp"])
    if y and ct>=t and ct<t+H:return 1,ct
    return 0,t+H
def clamp(x):return min(1-1e-12,max(1e-12,x))
def feats(r):
    return [int.from_bytes(hashlib.blake2b((k+"="+r[k]).encode(),digest_size=8).digest(),"little")%DIM for k in ("cat1","cat2","campaign")]
def main():
    p=Path("criteo_attribution_dataset.tsv.gz")
    download(p)
    if p.stat().st_size!=SIZE:raise ValueError("Source byte-count mismatch")
    if digest(p)!=SHA:raise ValueError("Source SHA256 mismatch")
    n,lo,hi=scan(p)
    warm=lo+0.3*(hi-lo);devend=lo+0.7*(hi-lo)
    counts=[0,0];mc=[0,0];camp=defaultdict(lambda:[0,0]);camp_m=defaultdict(lambda:[0,0])
    recent=deque();weights=[0.0]*DIM;weights_m=[0.0]*DIM
    early=[];mature=[];loss=defaultdict(float);brier=defaultdict(float)
    i_dev=i_warm=receipts=receipts_m=0
    predhash=hashlib.sha256()
    last=-1
    for i,r in enumerate(rows(p)):
        t=int(r["timestamp"])
        if t>=devend:break
        if i%10:continue
        while early and early[0][0]<=t:
            _,ix,y,c,idx=heapq.heappop(early)
            counts[0]+=y;counts[1]+=1
            camp[c][0]+=y;camp[c][1]+=1
            recent.append((t,y))
            z=sum(weights[k] for k in idx)
            pred=1/(1+math.exp(-max(-30,min(30,z))))
            for k in idx:weights[k]-=LR*(pred-y)
            receipts+=1
        while mature and mature[0][0]<=t:
            _,ix,y,c,idx=heapq.heappop(mature)
            mc[0]+=y;mc[1]+=1
            camp_m[c][0]+=y;camp_m[c][1]+=1
            z=sum(weights_m[k] for k in idx)
            pred=1/(1+math.exp(-max(-30,min(30,z))))
            for k in idx:weights_m[k]-=LR*(pred-y)
            receipts_m+=1
        while recent and recent[0][0]<t-3*DAY:recent.popleft()
        c=r["campaign"]; idx=feats(r)
        ep=(counts[0]+P*SMOOTH)/(counts[1]+SMOOTH)
        mp=(mc[0]+P*SMOOTH)/(mc[1]+SMOOTH)
        cr=camp[c];cm=camp_m[c]
        z=sum(weights[k] for k in idx);zm=sum(weights_m[k] for k in idx)
        pred={
           "fixed_prior":P,
           "global_event":ep,
           "rolling_event":(sum(a for _,a in recent)+P*SMOOTH)/(len(recent)+SMOOTH),
           "campaign_event":(cr[0]+ep*CAMP)/(cr[1]+CAMP),
           "global_mature":mp,
           "campaign_mature":(cm[0]+mp*CAMP)/(cm[1]+CAMP),
           "hashed_logit_event":1/(1+math.exp(-max(-30,min(30,z)))),
           "hashed_logit_mature":1/(1+math.exp(-max(-30,min(30,zm))))}
        y,rel=label(r,t)
        if t>=warm:
            i_dev+=1
            for k,prob in pred.items():
                prob=clamp(prob);loss[k]-=y*math.log(prob)+(1-y)*math.log1p(-prob)
                brier[k]+=(y-prob)**2
            predhash.update((str(i)+"|"+",".join(f"{pred[k]:.12g}" for k in sorted(pred))+"\n").encode())
        else:i_warm+=1
        heapq.heappush(early,(rel,i,y,c,idx))
        heapq.heappush(mature,(t+H,i,y,c,idx))
    if not i_dev:raise ValueError("No development rows")
    report={"status":"EXPLORATORY_REAL_EVENT_TIME","source_verified_sha256":SHA,"source_rows":n,
            "source_time_min":lo,"source_time_max":hi,"warmup_end":warm,"development_end":devend,
            "warmup_predictions":i_warm,"development_predictions":i_dev,"holdout_outcomes_evaluated":0,
            "feedback_event_receipts":receipts,"feedback_mature_receipts":receipts_m,
            "sample_every":10,"event_time_not_verified_arrival_time":True,"prediction_sha256":predhash.hexdigest(),
            "metrics":{k:{"logloss":loss[k]/i_dev,"brier":brier[k]/i_dev} for k in sorted(loss)}}
    Path("criteo_dev_metrics.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
