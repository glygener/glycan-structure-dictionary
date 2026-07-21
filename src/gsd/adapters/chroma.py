from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

# --- SQLite shim -----------------------------------------------------------
# chromadb (imported transitively by langchain_chroma) requires sqlite3 >= 3.35.
# When the standard-library sqlite3 is too old (or otherwise unusable), swap in
# the standalone `pysqlite3` library BEFORE any chromadb import so the
# Ollama-embedding vector store still builds/loads. No langchain_community
# fallback — if the SQLite library is missing we fail loudly with a fix.
import sys as _sys
import sqlite3 as _sqlite3

if _sqlite3.sqlite_version_info < (3, 35, 0):
    try:
        import pysqlite3 as _pysqlite3  # type: ignore
    except ModuleNotFoundError as _exc:  # pragma: no cover - env-dependent
        raise RuntimeError(
            "chromadb requires sqlite3 >= 3.35, but the standard library "
            f"provides {_sqlite3.sqlite_version}. Install the standalone SQLite "
            "library with `pip install pysqlite3-binary`."
        ) from _exc
    _sys.modules["sqlite3"] = _pysqlite3
    _sys.modules["sqlite3.dbapi2"] = _pysqlite3.dbapi2
# ---------------------------------------------------------------------------

from langchain_core.documents import Document

try:
    from langchain_chroma import Chroma
except ModuleNotFoundError as exc:  # pragma: no cover - explicit dependency
    raise ModuleNotFoundError(
        "The 'langchain-chroma' package is required. "
        "Install it with `pip install langchain-chroma`."
    ) from exc

try:
    from langchain_ollama import OllamaEmbeddings
except ModuleNotFoundError as exc:  # pragma: no cover - explicit dependency
    raise ModuleNotFoundError(
        "The 'langchain-ollama' package is required for Ollama embeddings. "
        "Install it with `pip install langchain-ollama`."
    ) from exc


def build_ollama_embeddings(model_name: str, host: str) -> OllamaEmbeddings:
    """Create an Ollama embedding client."""
    return OllamaEmbeddings(model=model_name, base_url=host)


def build_chroma_from_documents(
    documents: Sequence[Document],
    *,
    collection_name: str,
    persist_directory: str | Path,
    embedding_model: str,
    ollama_host: str,
    ids: Sequence[str] | None = None,
) -> Chroma:
    """Create and persist a Chroma vector store from input documents."""
    persist_path = Path(persist_directory)
    persist_path.mkdir(parents=True, exist_ok=True)

    embeddings = build_ollama_embeddings(embedding_model, ollama_host)
    return Chroma.from_documents(
        documents=list(documents),
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(persist_path),
        ids=list(ids) if ids is not None else None,
    )


def load_chroma_documents(
    *, persist_directory: str | Path, collection_name: str
) -> list[tuple[str, str, dict[str, Any]]]:
    """Load all stored documents from a Chroma collection."""
    import chromadb

    persist_path = Path(persist_directory)
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_collection(name=collection_name)
    payload = collection.get(include=["documents", "metadatas"])

    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []

    rows: list[tuple[str, str, dict[str, Any]]] = []
    for chunk_id, document, metadata in zip(ids, documents, metadatas):
        if not isinstance(document, str):
            continue
        rows.append((str(chunk_id), document, dict(metadata or {})))
    return rows
