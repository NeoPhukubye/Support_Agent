import os

import chromadb
from chromadb.utils import embedding_functions

from config import settings

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    _client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = _client.get_or_create_collection(
        name="support_kb",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Seed only if empty
    if _collection.count() == 0:
        _seed_documents()

    return _collection


def _seed_documents():
    docs, ids, metas = [], [], []
    chunk_id = 0
    for fname in os.listdir(DOCS_DIR):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(DOCS_DIR, fname)
        with open(path, "r") as f:
            content = f.read()
        # Split into chunks using configured chunk size
        chunk_size = settings.kb_chunk_size
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        for chunk in chunks:
            docs.append(chunk)
            ids.append(f"doc_{chunk_id}")
            metas.append({"source": fname})
            chunk_id += 1

    if docs:
        _get_collection().add(documents=docs, ids=ids, metadatas=metas)
        print(f"[KB] Seeded {len(docs)} chunks from {DOCS_DIR}")


def search_knowledge_base(query: str, n_results: int | None = None) -> list[dict]:
    col = _get_collection()
    if n_results is None:
        n_results = settings.kb_search_results
    results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return [{"content": d, "source": m.get("source", "")} for d, m in zip(docs, metas)]