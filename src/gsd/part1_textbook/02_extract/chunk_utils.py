from __future__ import annotations

"""Chunk loading, pairing, overlap trimming, and sentence-level utilities.

Extracted from the original monolithic 02_extract.py so the LangGraph workflow
and any future pipelines can reuse these helpers without duplication.
"""

import json
import re
from pathlib import Path
from typing import Any

from gsd.adapters.chroma import load_chroma_documents

SENTENCE_TAG_RE = re.compile(r"<S:(\d+)>")
_SENTENCE_BLOCK_RE = re.compile(r"<S:(\d+)>(.*?)</S:\1>", re.DOTALL)


# ---------------------------------------------------------------------------
# Sentence helpers
# ---------------------------------------------------------------------------


def extract_sentence_text(tagged_text: str, sentence_index: int) -> str | None:
    """Return the raw sentence text for a given <S:N> index, or None."""
    for match in _SENTENCE_BLOCK_RE.finditer(tagged_text):
        if int(match.group(1)) == sentence_index:
            return match.group(2).strip()
    return None


def first_sentence_index(tagged_text: str) -> int:
    """Return the first <S:N> sentence index found in a tagged chunk, or 0."""
    match = SENTENCE_TAG_RE.search(tagged_text)
    return int(match.group(1)) if match else 0


def get_sentence_indices(tagged_text: str) -> set[int]:
    """Return the set of all <S:N> sentence indices present in a tagged chunk."""
    return {int(m) for m in SENTENCE_TAG_RE.findall(tagged_text)}


# ---------------------------------------------------------------------------
# Sentence UUID map
# ---------------------------------------------------------------------------


def load_sentence_uuid_map(path: Path) -> dict[tuple[int, int], str]:
    """Map (chapter, sentence_index) -> src_uuid from a JSONL sentence index file."""
    mapping: dict[tuple[int, int], str] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            mapping[(int(row["chapter"]), int(row["index"]))] = row["src_uuid"]
    return mapping


# ---------------------------------------------------------------------------
# Chunk document loading
# ---------------------------------------------------------------------------


def load_chunk_documents(
    persist_directory: Path, collection_name: str
) -> list[tuple[str, int, str]]:
    """Load all EOG chunk documents from Chroma, sorted by (chapter, first_sentence, chunk_id).

    Returns list of (chunk_id, chapter, document_text).
    """
    rows: list[tuple[str, int, str, int]] = []
    for chunk_id, doc, metadata in load_chroma_documents(
        persist_directory=persist_directory,
        collection_name=collection_name,
    ):
        if not isinstance(doc, str) or not doc.strip():
            continue
        chapter_raw = (metadata or {}).get("chapter")
        if chapter_raw is None:
            continue
        rows.append((str(chunk_id), int(chapter_raw), doc, first_sentence_index(doc)))

    rows.sort(key=lambda r: (r[1], r[3], r[0]))
    return [(chunk_id, chapter, doc) for chunk_id, chapter, doc, _ in rows]


# ---------------------------------------------------------------------------
# Chunk pairing (overlap trimming + merging)
# ---------------------------------------------------------------------------


def trim_overlap(chunk_text: str, preceding_indices: set[int]) -> str:
    """Strip leading sentences from chunk_text that are already in preceding_indices.

    Returns an empty string when all sentences in chunk_text duplicate the preceding chunk.
    """
    for match in SENTENCE_TAG_RE.finditer(chunk_text):
        if int(match.group(1)) not in preceding_indices:
            return chunk_text[match.start():]
    return ""


def merge_two_chunks(
    chunk_a: tuple[str, int, str],
    chunk_b: tuple[str, int, str],
) -> tuple[str, int, str]:
    """Merge two consecutive same-chapter chunks into one, removing the overlap preamble.

    Returns (merged_chunk_id, chapter, merged_text).
    """
    chunk_id_a, chapter, text_a = chunk_a
    chunk_id_b, _, text_b = chunk_b
    indices_a = get_sentence_indices(text_a)
    trimmed_b = trim_overlap(text_b, indices_a)
    merged_text = text_a + ("\n" + trimmed_b if trimmed_b else "")
    return f"{chunk_id_a} + {chunk_id_b}", chapter, merged_text


def pair_chunks(
    chunks: list[tuple[str, int, str]],
) -> list[tuple[str, int, str]]:
    """Merge consecutive same-chapter chunk pairs to halve the number of LLM invocations.

    Chunks must already be sorted by (chapter, first_sentence, chunk_id).
    """
    merged: list[tuple[str, int, str]] = []
    i = 0
    while i < len(chunks):
        a = chunks[i]
        if i + 1 < len(chunks) and chunks[i + 1][1] == a[1]:  # same chapter
            merged.append(merge_two_chunks(a, chunks[i + 1]))
            i += 2
        else:
            merged.append(a)
            i += 1
    return merged


# ---------------------------------------------------------------------------
# Output path resolution
# ---------------------------------------------------------------------------


def resolve_output_path(paths_cfg: dict[str, Any], output_path: Path | None) -> Path:
    """Resolve the destination JSONL path for extracted mentions."""
    if output_path is not None:
        return output_path
    eog_paths = paths_cfg["resources"]["eog"]
    if "term_mentions" in eog_paths:
        output_dir = eog_paths["term_mentions"]
    else:
        output_dir = eog_paths["indexed_sentences"].parent / "term_mentions"
    return output_dir / "eog_glycan_term_mentions.jsonl"


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def build_extraction_user_prompt(chapter: int, chunk_id: str, tagged_chunk: str) -> str:
    """Build the extraction user prompt for one tagged chunk (or merged pair)."""
    return (
        f"Chapter: {chapter}\n"
        f"Chunk ID: {chunk_id}\n\n"
        "Extract glycan structural terms from this chunk:\n\n"
        f"{tagged_chunk}"
    )
