from pathlib import Path
from typing import Any
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = ROOT / "data" / "chroma"
_embedder = None
_embedder_path = None
_collection = None
_private_collections = {}
_closed_private_sessions = set()

def collection(tenant_id: str = "default", private_session: str | None = None):
    if private_session:
        key = f"{tenant_id}:{private_session}"
        if key not in _private_collections:
            client = chromadb.EphemeralClient()
            _private_collections[key] = client.get_or_create_collection(f"private_{private_session[:32]}", metadata={"hnsw:space": "cosine"})
        return _private_collections[key]
    global _collection
    if _collection is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection("rag_revolver_documents", metadata={"hnsw:space": "cosine"})
    return _collection

def clear_private_session(tenant_id: str, private_session: str) -> bool:
    """Forget an in-memory private collection and all of its vectors."""
    if not private_session:
        return False
    key = f"{tenant_id}:{private_session}"
    deleted = _private_collections.pop(key, None) is not None
    _closed_private_sessions.add(key)
    return deleted

def embedder():
    global _embedder, _embedder_path
    selected = "BAAI/bge-small-en-v1.5"
    db = ROOT / "data" / "revolver.sqlite3"
    if db.exists():
        try:
            c = sqlite3.connect(db)
            row = c.execute("SELECT version FROM model_versions WHERE status='live' ORDER BY id DESC LIMIT 1").fetchone()
            c.close()
            if row:
                candidate = ROOT / "models" / row[0]
                if candidate.exists() and (candidate / "config.json").exists(): selected = str(candidate)
        except sqlite3.Error:
            pass
    if _embedder is None or _embedder_path != selected:
        _embedder = SentenceTransformer(selected)
        _embedder_path = selected
    return _embedder

def active_model():
    model = embedder()
    return {"path": _embedder_path, "custom": _embedder_path != "BAAI/bge-small-en-v1.5"}

def rebuild_index():
    """Re-embed persisted Chroma documents after activating a new model."""
    stores = [collection()]
    rebuilt = 0
    for store in stores:
        if store.count() == 0: continue
        data = store.get(include=["documents", "metadatas"])
        documents = data.get("documents") or []
        if not documents: continue
        vectors = embedder().encode(documents, normalize_embeddings=True).tolist()
        store.upsert(ids=data["ids"], documents=documents, embeddings=vectors, metadatas=data.get("metadatas"))
        rebuilt += len(documents)
    return rebuilt

def add_chunks(chunks: list[dict[str, Any]], tenant_id: str = "default", user_id: str = "anonymous", private_session: str | None = None) -> int:
    if not chunks:
        return 0
    vectors = embedder().encode([c["text"] for c in chunks], normalize_embeddings=True).tolist()
    metadata=[]
    for c in chunks:
        item=dict(c["metadata"]); item.update({"tenant_id":tenant_id,"user_id":user_id,"private":bool(private_session)}); metadata.append(item)
    collection(tenant_id, private_session).upsert(ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks], embeddings=vectors, metadatas=metadata)
    return len(chunks)

def search(query: str, limit: int = 4, tenant_id: str = "default", user_id: str = "anonymous", private_session: str | None = None) -> list[dict[str, Any]]:
    if private_session and f"{tenant_id}:{private_session}" in _closed_private_sessions:
        return []
    store=collection(tenant_id, private_session)
    if store.count() == 0:
        return []
    vector = embedder().encode([query], normalize_embeddings=True).tolist()
    where=None if private_session else {"tenant_id":tenant_id}
    result = store.query(query_embeddings=vector, n_results=limit, where=where, include=["documents", "metadatas", "distances"])
    return [{"text": text, "metadata": metadata, "distance": distance} for text, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])]
