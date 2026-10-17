"""Train and evaluate a versioned Mender embedding model.

Real demo run:
    python train_mender.py --version bge-revolver-demo-001 --demo --epochs 1

The demo uses synthetic pairs only to prove the pipeline. A real run uses
approved rows from SQLite and a held-out JSON file supplied with --eval-file.
The candidate is always stored as pending until the approval endpoint is used.
"""
import argparse, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "revolver.sqlite3"
DEMO_FILE = Path(__file__).with_name("mender_demo.json")

def read_json(path):
    with path.open("r", encoding="utf-8") as handle: return json.load(handle)

def approved_pairs():
    if not DB.exists(): return []
    c=sqlite3.connect(DB); rows=c.execute("SELECT question,answer,positive_source FROM training_pairs WHERE status='approved'").fetchall(); c.close()
    return [{"question":q,"passage":answer or source} for q,answer,source in rows if q and (answer or source)]

def score_model(model, examples):
    if not examples: return {"count":0,"k":4,"hit_at_4":None,"mrr":None}
    hits=[]; reciprocal=[]
    for item in examples:
        candidates=item["candidates"]; qv=model.encode([item["question"]],normalize_embeddings=True)[0]; pv=model.encode(candidates,normalize_embeddings=True); scores=np.asarray(pv) @ np.asarray(qv); ranking=np.argsort(-scores).tolist(); positive=int(item.get("positive_index",0)); rank=ranking.index(positive)+1 if positive in ranking else None
        hits.append(bool(rank and rank<=4)); reciprocal.append(1/rank if rank else 0)
    return {"count":len(examples),"k":4,"hit_at_4":sum(hits)/len(hits),"mrr":sum(reciprocal)/len(reciprocal)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--version',required=True); parser.add_argument('--epochs',type=int,default=1); parser.add_argument('--eval-file',type=Path); parser.add_argument('--demo',action='store_true'); args=parser.parse_args()
    dataset=read_json(args.eval_file or DEMO_FILE) if args.demo or args.eval_file else None; pairs=dataset['train'] if dataset else approved_pairs(); evaluation=dataset['test'] if dataset else []
    if len(pairs)<2: raise SystemExit('Need at least 2 approved training pairs, or run with --demo.')
    if not evaluation: raise SystemExit('Provide --eval-file with held-out candidates, or run with --demo.')
    examples=[InputExample(texts=[item['question'],item['passage']]) for item in pairs]; model=SentenceTransformer('BAAI/bge-small-en-v1.5'); loader=DataLoader(examples,shuffle=True,batch_size=min(8,len(examples))); loss=losses.MultipleNegativesRankingLoss(model)
    out=ROOT/'models'/args.version; out.mkdir(parents=True,exist_ok=True); model.fit(train_objectives=[(loader,loss)],epochs=args.epochs,output_path=str(out),show_progress_bar=True)
    metrics=score_model(SentenceTransformer(str(out)),evaluation); metrics.update({'train_pairs':len(pairs),'epochs':args.epochs,'base_model':'BAAI/bge-small-en-v1.5','eval_set':'held_out'}); (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    c=sqlite3.connect(DB); c.execute("CREATE TABLE IF NOT EXISTS model_versions (id INTEGER PRIMARY KEY,version TEXT UNIQUE,metrics_json TEXT,status TEXT,created_at TEXT)"); c.execute("INSERT OR REPLACE INTO model_versions(version,metrics_json,status,created_at) VALUES(?,?,?,?)",(args.version,json.dumps(metrics),'pending',datetime.now(timezone.utc).isoformat())); c.commit(); c.close()
    print(json.dumps({'version':args.version,'path':str(out),'status':'candidate_pending_approval','metrics':metrics},indent=2))

if __name__=='__main__': main()
