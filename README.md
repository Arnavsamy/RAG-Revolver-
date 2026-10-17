# RAG / Revolver

Local-first RAG workbench with a Three.js revolver picker, FastAPI streaming traces, SQLite event logs, and honest empty states. The frontend is runnable without a configured model or document set; it will show exactly what is missing instead of inventing metrics.

## Run

Terminal 1 (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Terminal 2 (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` calls to the FastAPI server on port 8000.

## Hermes provider

Hermes is an explicit backend provider. Set its OpenAI-compatible service URL before using it:

```text
HERMES_BASE_URL=http://localhost:8001
HERMES_MODEL=hermes
HERMES_CHAT_PATH=/v1/chat/completions
HERMES_HEALTH_PATH=/health
```

Then send a chat request with `"hermes_mode": true`. Check the connection with `GET /api/hermes/status?probe=true`. The backend never claims Hermes is live unless the URL is configured and the health probe succeeds. For private mode, Hermes is allowed only when the URL is local and `HERMES_PRIVATE_MODE=true`; otherwise private requests are blocked from sending document content to a remote Hermes service.

## Measurement contract

- **Mender:** hold out question/passage pairs, report hit@4 and MRR before/after. New models remain pending approval and versioned under `models/`.
- **Skill Forge:** compare run 1 and run 2 wall time and model/tool cost after saving a skill.
- **Adversary:** report attack success rate on a fixed attack set before/after defenses and export the trace.
- **Conflict Hunter:** store extracted claims with source/page citations and report coverage; disagreement rows are evidence, not a score.
- **Recall:** every note has a timestamp and deletion path; “as of” queries filter by date and flag stale/contradictory notes.
- **Sentinel:** store watch snapshots, diffs, summaries and delivery status; Telegram sends are approval-gated.

Training is intentionally approval-gated and versioned. The included local demo proves the complete path with a held-out evaluation set:

```powershell
..\venv\Scripts\python.exe backend\train_mender.py --version bge-revolver-demo-001 --demo --epochs 1
```

The command fine-tunes `BAAI/bge-small-en-v1.5`, writes the model to `models/<version>/`, writes `metrics.json`, and records the candidate as `candidate_pending_approval` in SQLite. The demo currently reports real held-out `hit_at_4` and `mrr` values; the four demo pairs are synthetic and should be replaced with approved pairs from your own documents for a meaningful domain result.

To use real data, approve Mender training pairs first, then run the same script without `--demo` (optionally pass a held-out JSON file with `--eval-file`). A candidate is not used for retrieval until the model approval route is completed:

```text
POST /api/mender/models/<version>/approve
POST /api/workflow/approvals/<approval_id>/approve
```

Approval marks the model live, re-embeds the persistent Chroma index with that model, and exposes the active path through `/api/health`. Chroma is included in backend dependencies and is initialized when ingestion is used.

## Next implementation slices

The UI and API establish the shared bot interface, live trace protocol, approval boundary, and measurement surface. Add ingestion and evaluation workers behind the same `bot_id` routes; do not populate charts until real eval rows exist.
