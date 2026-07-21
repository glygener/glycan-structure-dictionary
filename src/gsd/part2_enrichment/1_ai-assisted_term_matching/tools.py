from __future__ import annotations

"""LangChain tools for the entity-resolution workflow.

Currently provides:
  query_textbook — RAG-style retrieval over the Essentials of Glycobiology (EoG)
                   Chroma vectorstore. Returns concatenated sentence excerpts
                   that ground the resolver's decision in textbook biology.
"""

from pathlib import Path
import sys

from langchain_core.tools import tool

_PKG_DIR = Path(__file__).resolve().parent
SRC_ROOT = _PKG_DIR.parents[2]  # src/
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gsd.adapters import build_embeddings
from gsd.config import (
    load_chroma_config,
    load_models_config,
    load_paths_config,
)

# Import Chroma via the adapter so the sqlite3 shim runs before chromadb loads
# (and without any langchain_community fallback).
from gsd.adapters.chroma import Chroma


_EOG_STORE = None
_MAX_CHUNK_CHARS = 350
_MAX_TOTAL_CHARS = 1400  # keep total textbook block compact for MLX-runner-safe prompts


def _get_eog_store():
    """Lazy-load the EoG Chroma vector store (singleton)."""
    global _EOG_STORE
    if _EOG_STORE is not None:
        return _EOG_STORE

    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()

    eog_cfg = chroma_cfg.get("eog", {})
    persist_dir = eog_cfg.get(
        "persist_directory",
        str(Path(paths_cfg["workspace"]["chroma"]) / "eog"),
    )
    collection = eog_cfg.get("collection_name", "eog_chunks")
    embeddings = build_embeddings()

    _EOG_STORE = Chroma(
        persist_directory=str(persist_dir),
        collection_name=collection,
        embedding_function=embeddings,
    )
    return _EOG_STORE


def _strip_sentence_tags(text: str) -> str:
    """Remove <S:n>...</S:n> sentence-id tags inserted at chunk creation time."""
    import re
    return re.sub(r"</?S:\d+>", "", text).strip()


def _format_results(results) -> str:
    if not results:
        return "(no textbook context found)"

    lines: list[str] = []
    total_chars = 0
    for doc, score in results:
        excerpt = _strip_sentence_tags(doc.page_content)
        if len(excerpt) > _MAX_CHUNK_CHARS:
            excerpt = excerpt[:_MAX_CHUNK_CHARS] + "..."
        chap = doc.metadata.get("chapter_id") or f"ch{doc.metadata.get('chapter', '?')}"
        line = f"[{chap}, score={round(score, 3)}] {excerpt}"
        if total_chars + len(line) > _MAX_TOTAL_CHARS:
            break
        lines.append(line)
        total_chars += len(line) + 1

    return "\n".join(lines).strip() or "(no textbook context found)"


@tool
def query_textbook(query: str, max_results: int = 3) -> str:
    """Search Essentials of Glycobiology (EoG, 4e) for context on a glycan term.

    Use this when the candidate matches are ambiguous and you would benefit from
    textbook-level biology to decide whether the query term refers to the same
    glycan as a candidate, or a distinct structure / concept.

    Args:
        query: A concise free-text query. Mention the glycan name plus what
               you want to clarify, e.g. "sialyl Lewis x structure", "GD1a
               ganglioside", "asialo-GM1 abbreviation synonyms".
        max_results: Number of chunks to retrieve (default 3, max 5).

    Returns:
        Formatted string of chapter-tagged excerpts from the textbook.
    """
    max_results = max(1, min(int(max_results), 5))
    try:
        store = _get_eog_store()
        results = store.similarity_search_with_relevance_scores(
            query=query,
            k=max_results,
            score_threshold=0.2,
        )
        return _format_results(results)
    except Exception as exc:
        return f"(textbook search failed: {exc})"
