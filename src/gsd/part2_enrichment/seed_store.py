"""Seed the GSD enrichment vector store from the primary source (src_eog).

This script creates the initial Chroma vector store that the entity resolver
graph.py queries when processing subsequent sources (src_gsdv0, etc.).

The seed source (src_eog) already has assigned term_uuids, so each term becomes
a document in the vector store keyed by its GSD UUID.

Usage:
    python seed_store.py [--seed-source src_eog] [--extra-sources src_foo src_bar]
"""

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

SRC_ROOT = Path(__file__).resolve().parents[2]  # src/
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gsd.adapters import build_embeddings

# Import Chroma via the adapter so the sqlite3 shim runs before chromadb loads
# (and without any langchain_community fallback).
from gsd.adapters.chroma import Chroma
from gsd.config import (
    load_chroma_config,
    load_models_config,
    load_ollama_config,
    load_paths_config,
)

COLLECTION_NAME = "glycan_structure_dictionary"


def load_terms_as_documents(terms_file: Path) -> list[Document]:
    """Convert a source terms.jsonl into LangChain Documents for the vector store."""
    documents = []
    with open(terms_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)

            term = entry.get("term", "").strip()
            if not term or term == "[DISCARD]":
                continue

            term_uuid = entry.get("term_uuid", "").strip()
            if not term_uuid:
                term_uuid = f"GSD:{uuid4()}"

            metadata = entry.get("metadata", {})
            exact_synonyms = metadata.get("exact_synonyms", []) or []
            description = metadata.get("description") or metadata.get("definition") or ""
            gtc_id = metadata.get("gtc_id", []) or []
            if isinstance(gtc_id, str):
                gtc_id = [gtc_id] if gtc_id else []

            syn_str = ", ".join(exact_synonyms) if exact_synonyms else ""
            page_content = (
                f"Term: {term}\n"
                f"Exact Synonyms: {syn_str}\n"
                f"Description: {description}\n"
                f"Term UUID: {term_uuid}"
            )

            doc = Document(
                page_content=page_content,
                metadata={
                    "term": term,
                    "term_uuid": term_uuid,
                    "exact_synonyms": json.dumps(exact_synonyms, ensure_ascii=False),
                    "description": description or "",
                    "gtc_id": json.dumps(gtc_id, ensure_ascii=False),
                },
                id=term_uuid,
            )
            documents.append(doc)

    return documents


def seed_vector_store(
    seed_source: str = "src_eog",
    extra_sources: list[str] | None = None,
) -> Path:
    """Build the enrichment Chroma vector store from seed source(s).

    Parameters
    ----------
    seed_source : str
        Primary source directory name (default: "src_eog").
    extra_sources : list[str] | None
        Additional source directories whose already-resolved terms
        should be included (e.g. sources that already have term_uuids).

    Returns
    -------
    Path
        The persist directory of the created vector store.
    """
    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()

    inputs_dir = Path(paths_cfg["data"]["inputs"])

    # Determine persist directory
    enrichment_cfg = chroma_cfg.get("enrichment", {})
    persist_dir = Path(
        enrichment_cfg.get(
            "persist_directory",
            str(Path(paths_cfg["workspace"]["chroma"]) / "enrichment"),
        )
    )
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Collect all sources to seed
    sources = [seed_source]
    if extra_sources:
        sources.extend(extra_sources)

    all_documents = []
    seen_uuids: set[str] = set()

    for source in sources:
        terms_file = inputs_dir / source / "terms.jsonl"
        if not terms_file.exists():
            print(f"[WARN] No terms.jsonl for {source}, skipping")
            continue

        docs = load_terms_as_documents(terms_file)

        # Deduplicate by term_uuid
        for doc in docs:
            uid = doc.metadata.get("term_uuid", "")
            if uid and uid not in seen_uuids:
                seen_uuids.add(uid)
                all_documents.append(doc)
            elif uid in seen_uuids:
                print(f"[DEDUP] Skipping duplicate UUID {uid} from {source}")

        print(f"[SEED] Loaded {len(docs)} terms from {source} ({len(all_documents)} total)")

    if not all_documents:
        print("[ERROR] No documents to seed. Check source paths.")
        return persist_dir

    # Build the vector store with provider-agnostic embeddings.
    models_cfg = load_models_config()
    provider = (models_cfg.get("provider") or "ollama").lower()
    embeddings = build_embeddings()

    print(f"\n[BUILD] Creating Chroma vector store with {len(all_documents)} documents...")
    print(f"[BUILD] Persist directory: {persist_dir}")
    print(f"[BUILD] Collection name: {COLLECTION_NAME}")
    print(f"[BUILD] Embedding provider: {provider}")

    ids = [doc.id for doc in all_documents]
    vector_store = Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
        ids=ids,
        collection_metadata={"hnsw:space": "cosine"},
    )

    print(f"[BUILD] Successfully created vector store with {len(all_documents)} documents")

    # Verification retrieval
    print("\n--- Verification retrieval ---")
    test_queries = ["lewis antigen", "sialic acid", "GM1 ganglioside"]
    for query in test_queries:
        results = vector_store.similarity_search_with_relevance_scores(query, k=2)
        print(f"Query: '{query}'")
        for doc, score in results:
            print(f"  -> {doc.metadata['term']} (score={score:.4f})")

    return persist_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the GSD enrichment vector store from source JSONL files."
    )
    parser.add_argument(
        "--seed-source",
        type=str,
        default="src_eog",
        help="Primary source to seed the store (default: src_eog).",
    )
    parser.add_argument(
        "--extra-sources",
        type=str,
        nargs="*",
        default=None,
        help="Additional sources to include in the seed.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_vector_store(
        seed_source=args.seed_source,
        extra_sources=args.extra_sources,
    )
