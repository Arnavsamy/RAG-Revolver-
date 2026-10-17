import asyncio, json, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pypdf import PdfReader
from rag import add_chunks, search, active_model, clear_private_session
from bots import router as bots_router, sentinel_scheduler
from providers import configured_models, generate, hermes_status
from backups import create_backup, list_backups, restore_backup

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "revolver.sqlite3"
app = FastAPI(title="RAG Revolver API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(bots_router)

@app.on_event("startup")
async def start_sentinel_scheduler():
    asyncio.create_task(sentinel_scheduler())

def db():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, bot_id TEXT, kind TEXT, payload TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS bot_runs (id INTEGER PRIMARY KEY, bot_id TEXT, input_json TEXT, output_json TEXT, status TEXT, created_at TEXT)")
    conn.commit(); return conn

def log_event(bot_id: str, kind: str, payload: dict):
    stamp=datetime.now(timezone.utc).isoformat(); conn=db(); conn.execute("INSERT INTO events(bot_id,kind,payload,created_at) VALUES(?,?,?,?)",(bot_id,kind,json.dumps(payload),stamp)); conn.commit(); conn.close()

class Chat(BaseModel):
    bot_id: str
    message: str
    model: str = "router"
    tenant_id: str = "default"
    user_id: str = "anonymous"
    private_mode: bool = False
    private_session: str | None = None
    hermes_mode: bool = False

@app.get("/api/health")
def health(): return {"ok": True, "data": str(DATA), "vector_store": "chroma", "model_router": ["hermes", "groq", "gemini"], "configured_models": configured_models(), "embedding_model": active_model(), "metrics": "empty_until_evaluated"}

@app.get("/api/hermes/status")
def hermes_connection_status(probe: bool = False):
    return hermes_status(probe=probe)

@app.get("/api/bots")
def bots():
    return [{"id": "mender", "status": "Live"}, {"id": "skill-forge", "status": "Beta"}, {"id": "adversary", "status": "Beta"}, {"id": "conflict-hunter", "status": "Live"}, {"id": "recall", "status": "Live"}, {"id": "sentinel", "status": "Beta"}]

@app.get("/api/history")
def history(limit: int = 100):
    conn=db(); rows=conn.execute("SELECT bot_id AS category,kind AS event,payload,created_at FROM events UNION ALL SELECT bot_id, 'bot_run', output_json, created_at FROM bot_runs ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall(); conn.close()
    return {"items":[{"category":r[0],"event":r[1],"payload":json.loads(r[2]) if r[2] else {},"created_at":r[3]} for r in rows]}

@app.post("/api/backups/create")
def backup_create():
    result=create_backup(); log_event("system","backup_created",result); return result

@app.get("/api/backups")
def backups(): return {"items":list_backups()}

@app.post("/api/backups/{name}/restore")
def backup_restore(name: str):
    try: result=restore_backup(name)
    except FileNotFoundError: return {"ok":False,"error":"backup not found"}
    log_event("system","backup_restored",result); return {"ok":True,**result}

@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), tenant_id: str = Form("default"), user_id: str = Form("anonymous"), private_mode: bool = Form(False), private_session: str | None = Form(None)):
    raw = await file.read(); name = file.filename or "upload"; suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        import io
        pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(PdfReader(io.BytesIO(raw)).pages)]
    elif suffix in {".txt", ".md"}:
        pages = [(1, raw.decode("utf-8", errors="ignore"))]
    else:
        return {"ok": False, "error": "Supported formats: PDF, TXT, MD"}
    chunks = []
    private_session = (private_session or str(uuid.uuid4())) if private_mode else None
    for page, text in pages:
        clean = " ".join(text.split())
        for offset in range(0, len(clean), 900):
            part = clean[offset:offset + 1200]
            if part.strip():
                chunks.append({"id": str(uuid.uuid4()), "text": part, "metadata": {"source": name, "page": page, "chunk": offset // 900}})
    return {"ok": True, "filename": name, "chunks": add_chunks(chunks, tenant_id, user_id, private_session), "tenant_id": tenant_id, "private_mode": private_mode, "private_session": private_session}

@app.delete("/api/privacy/sessions/{private_session}")
def delete_private_session(private_session: str, tenant_id: str = "default"):
    """Delete one ephemeral private session from this backend process."""
    deleted = clear_private_session(tenant_id, private_session)
    return {"ok": True, "deleted": deleted, "private_session": private_session}

@app.get("/api/metrics/{bot_id}")
def metrics(bot_id: str):
    """Return only persisted measurements; an empty list is a valid first-run state."""
    conn = db()
    rows = conn.execute("SELECT payload, created_at FROM events WHERE bot_id=? AND kind='metric' ORDER BY id", (bot_id,)).fetchall()
    conn.close()
    return {"bot_id": bot_id, "measurements": [json.loads(row[0]) for row in rows]}

@app.get("/api/approvals")
def approvals():
    conn = db()
    rows = conn.execute("SELECT id, bot_id, payload, created_at FROM events WHERE kind='approval' ORDER BY id DESC").fetchall()
    conn.close()
    return {"items": [{"id": r[0], "bot_id": r[1], "payload": json.loads(r[2]), "created_at": r[3]} for r in rows]}

@app.post("/api/approvals/{event_id}/{decision}")
def decide_approval(event_id: int, decision: str):
    if decision not in {"approve", "reject"}:
        return {"ok": False, "error": "decision must be approve or reject"}
    conn = db(); conn.execute("UPDATE events SET payload=? WHERE id=? AND kind='approval'", (json.dumps({"decision": decision}), event_id)); conn.commit(); conn.close()
    return {"ok": True, "event_id": event_id, "decision": decision}

@app.post("/api/chat/stream")
async def chat_stream(chat: Chat):
    async def events():
        conn = db()
        if chat.private_mode and not chat.private_session:
            payload = {"type": "error", "message": "Private Mode requires the private_session returned by private document upload.", "timestamp": datetime.now(timezone.utc).isoformat()}
            yield f"data: {json.dumps(payload)}\n\n"
            conn.close()
            return
        sources = search(chat.message, 4, chat.tenant_id, chat.user_id, chat.private_session if chat.private_mode else None)
        steps = [("trace", f"agent started · {chat.bot_id}"), ("privacy", "ephemeral private retrieval · not persisted to shared history" if chat.private_mode else "standard shared retrieval"), ("retrieval", f"retrieved {len(sources)} chunk(s) from Chroma")]
        if chat.hermes_mode:
            steps.append(("provider", "Hermes agent requested"))
        if not sources:
            steps.append(("answer", "No indexed documents found. Upload a PDF, TXT, or MD file first."))
        elif chat.hermes_mode and not os.getenv("HERMES_BASE_URL"):
            steps.append(("error", "Hermes is not configured. Set HERMES_BASE_URL before enabling Hermes mode."))
        elif chat.private_mode and not chat.hermes_mode and not os.getenv("OLLAMA_BASE_URL") and os.getenv("LOCAL_FALLBACK", "true").lower() not in {"1", "true", "yes", "on"}:
            steps.append(("error", "Private Mode requires Ollama or LOCAL_FALLBACK=true"))
        else:
            context = "\n\n".join(f"[{i+1}] {s['metadata']['source']} p.{s['metadata'].get('page', 1)}\n{s['text']}" for i, s in enumerate(sources))
            prompt = f"Answer only from the sources below. Cite sources using [1], [2]. If unsupported, say you do not know.\n\nSOURCES:\n{context}\n\nQUESTION: {chat.message}"
            try:
                answer, provider = await asyncio.to_thread(generate, prompt, chat.private_mode, chat.hermes_mode)
                if answer:
                    steps.extend([("model", provider), ("citation", ", ".join(f"{s['metadata']['source']} p.{s['metadata'].get('page', 1)}" for s in sources)), ("answer", answer)])
                else:
                    steps.append(("error", "Configure Hermes, Groq/Gemini, Ollama for private mode, or enable LOCAL_FALLBACK=true"))
            except Exception as exc:
                steps.append(("error", f"Model request failed: {exc}"))
        for kind, message in steps:
            payload = {"type": kind, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}
            if not chat.private_mode:
                conn.execute("INSERT INTO events(bot_id,kind,payload,created_at) VALUES(?,?,?,?)", (chat.bot_id, kind, json.dumps(payload), payload["timestamp"])); conn.commit()
            yield f"data: {json.dumps(payload)}\n\n"; await asyncio.sleep(.22)
        conn.close()
    return StreamingResponse(events(), media_type="text/event-stream")
