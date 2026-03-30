from __future__ import annotations

# Extract glycan structural terms from EOG Chroma chunks and map them to sentence-level src_uuid values.

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

from gsd.adapters.chroma import load_chroma_documents
from gsd.adapters.ollama import (
    EmptyOllamaResponseError,
    build_chat_ollama,
    invoke_json,
    log_invocation_metadata,
)
from gsd.config import load_chroma_config, load_paths_config

_SENTENCE_TAG_RE = re.compile(r"<S:(\d+)>")


# ---------------------------------------------------------------------------
# Asset loading
# ---------------------------------------------------------------------------


def _load_extraction_assets(paths_cfg: dict[str, Any]) -> tuple[str, set[str]]:
    """Load and assemble the system prompt and allowed classification codes.

    The extraction schema is an implementation detail used only to derive the
    set of valid classification codes; it is not returned to callers.
    """
    prompt_paths = paths_cfg["prompts"]
    schema_paths = paths_cfg["schemas"]

    extraction_prompt = Path(prompt_paths["glycan_term_extraction_from_tagged_chunk"]).read_text(
        encoding="utf-8"
    ).strip()
    classification_prompt = Path(prompt_paths["glycan_classification_scheme"]).read_text(
        encoding="utf-8"
    ).strip()

    system_prompt = (
        f"{extraction_prompt}\n\n"
        "Reference classification scheme:\n\n"
        f"{classification_prompt}"
    )

    with Path(schema_paths["eog_glycan_term_extraction"]).open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    enum_values = (
        schema.get("properties", {})
        .get("entities", {})
        .get("items", {})
        .get("properties", {})
        .get("classification", {})
        .get("enum", [])
    )
    allowed_classifications = {str(v).upper() for v in enum_values}

    return system_prompt, allowed_classifications


def _load_sentence_uuid_map(path: Path) -> dict[tuple[int, int], str]:
    """Map (chapter, sentence_index) → src_uuid from a JSONL sentence index file."""
    mapping: dict[tuple[int, int], str] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            mapping[(int(row["chapter"]), int(row["index"]))] = row["src_uuid"]
    return mapping


# ---------------------------------------------------------------------------
# Chunk document loading and pairing
# ---------------------------------------------------------------------------


def _first_sentence_index(tagged_text: str) -> int:
    """Return the first <S:N> sentence index found in a tagged chunk, or 0."""
    match = _SENTENCE_TAG_RE.search(tagged_text)
    return int(match.group(1)) if match else 0


def _load_chunk_documents(
    persist_directory: Path, collection_name: str
) -> list[tuple[str, int, str]]:
    """Load all EOG chunk documents from Chroma, sorted by (chapter, first_sentence, chunk_id)."""
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
        rows.append((str(chunk_id), int(chapter_raw), doc, _first_sentence_index(doc)))

    rows.sort(key=lambda r: (r[1], r[3], r[0]))
    return [(chunk_id, chapter, doc) for chunk_id, chapter, doc, _ in rows]


def _get_sentence_indices(tagged_text: str) -> set[int]:
    """Return the set of all <S:N> sentence indices present in a tagged chunk."""
    return {int(m) for m in _SENTENCE_TAG_RE.findall(tagged_text)}


def _trim_overlap(chunk_text: str, preceding_indices: set[int]) -> str:
    """Strip leading sentences from chunk_text that are already in preceding_indices.

    The text splitter's chunk_overlap copies ~200 characters from the end of
    chunk A to the start of chunk B.  Because sentences are tagged with <S:N>,
    we simply scan for the first opening tag whose index is *not* already
    covered and return the text from that point onward.  Returns an empty
    string when all sentences in chunk_text duplicate the preceding chunk.
    """
    for match in _SENTENCE_TAG_RE.finditer(chunk_text):
        if int(match.group(1)) not in preceding_indices:
            return chunk_text[match.start():]
    return ""


def _merge_two_chunks(
    chunk_a: tuple[str, int, str],
    chunk_b: tuple[str, int, str],
) -> tuple[str, int, str]:
    """Merge two consecutive same-chapter chunks into one, removing the overlap preamble.

    Returns (merged_chunk_id, chapter, merged_text).
    """
    chunk_id_a, chapter, text_a = chunk_a
    chunk_id_b, _, text_b = chunk_b
    indices_a = _get_sentence_indices(text_a)
    trimmed_b = _trim_overlap(text_b, indices_a)
    merged_text = text_a + ("\n" + trimmed_b if trimmed_b else "")
    return f"{chunk_id_a} + {chunk_id_b}", chapter, merged_text


def _pair_chunks(
    chunks: list[tuple[str, int, str]],
) -> list[tuple[str, int, str]]:
    """Merge consecutive same-chapter chunk pairs to halve the number of LLM invocations.

    Chunks already sorted by (chapter, first_sentence, chunk_id).  Consecutive
    pairs within the same chapter are merged via _merge_two_chunks; unpaired
    trailing chunks or chapter-boundary chunks are passed through unchanged.
    """
    merged: list[tuple[str, int, str]] = []
    i = 0
    while i < len(chunks):
        a = chunks[i]
        if i + 1 < len(chunks) and chunks[i + 1][1] == a[1]:  # same chapter
            merged.append(_merge_two_chunks(a, chunks[i + 1]))
            i += 2
        else:
            merged.append(a)
            i += 1
    return merged


# ---------------------------------------------------------------------------
# Entity normalization
# ---------------------------------------------------------------------------


def _normalize_entities(
    payload: dict[str, Any], allowed_classifications: set[str]
) -> list[tuple[str, int, str, str]]:
    """Validate, deduplicate, and sort extracted entities from a model JSON payload.

    Returns a list of (surface_form, first_sentence_index, classification, reason)
    sorted by (sentence_index, surface_form).

    Per-chunk deduplication keeps the lowest first_sentence_index for each
    surface_form.  Sentence index must be a positive integer; a bare digit
    string (e.g. "5") is also accepted as a defensive measure.
    """
    entities = payload.get("entities", [])
    if not isinstance(entities, list):
        return []

    first_seen: dict[str, tuple[int, str, str]] = {}
    for item in entities:
        if not isinstance(item, dict):
            continue

        surface_form = item.get("surface_form")
        raw_index = item.get("first_sentence_index")
        classification = item.get("classification")
        reason = item.get("reason")

        if not isinstance(surface_form, str) or not surface_form:
            continue
        if not isinstance(classification, str):
            continue
        if not isinstance(reason, str) or not reason.strip():
            continue

        classification = classification.strip().upper()
        if classification not in allowed_classifications:
            continue

        # Accept int directly; also coerce bare digit strings defensively.
        if isinstance(raw_index, str) and raw_index.isdigit():
            raw_index = int(raw_index)
        if not isinstance(raw_index, int) or raw_index < 1:
            continue
        sentence_index = raw_index

        previous = first_seen.get(surface_form)
        if previous is None or sentence_index < previous[0]:
            first_seen[surface_form] = (sentence_index, classification, reason.strip())

    return sorted(
        (
            (surface_form, idx, cls, rsn)
            for surface_form, (idx, cls, rsn) in first_seen.items()
        ),
        key=lambda r: (r[1], r[0]),
    )


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _build_user_prompt(chapter: int, chunk_id: str, tagged_chunk: str) -> str:
    """Build the extraction user prompt for one tagged chunk (or merged pair)."""
    return (
        f"Chapter: {chapter}\n"
        f"Chunk ID: {chunk_id}\n\n"
        "Extract glycan structural terms from this chunk:\n\n"
        f"{tagged_chunk}"
    )


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------


def _resolve_output_path(paths_cfg: dict[str, Any], output_path: Path | None) -> Path:
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
# Orchestration
# ---------------------------------------------------------------------------


def extract_eog_terms(output_path: Path | None = None, max_documents: int | None = None) -> Path:
    """Run LLM extraction over EOG chunk documents and write mapped mention JSONL."""
    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()

    eog_chroma_cfg = chroma_cfg["eog"]
    persist_directory = Path(eog_chroma_cfg["persist_directory"]).resolve()
    collection_name = eog_chroma_cfg["collection_name"]

    sentence_map_path = (
        paths_cfg["resources"]["eog"]["indexed_sentences"] / "eog_sentence_map.jsonl"
    )
    sentence_uuid_map = _load_sentence_uuid_map(sentence_map_path)
    system_prompt, allowed_classifications = _load_extraction_assets(paths_cfg)

    chunk_documents = _load_chunk_documents(persist_directory, collection_name)
    if max_documents is not None:
        chunk_documents = chunk_documents[:max_documents]

    # Pair consecutive same-chapter chunks → ~half the number of LLM invocations.
    invocation_documents = _pair_chunks(chunk_documents)

    destination = _resolve_output_path(paths_cfg, output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Build the model once — avoids re-reading config YAML on every iteration.
    chat_model = build_chat_ollama(model_key="extraction_model")

    written = 0
    skipped_blank = 0
    skipped_no_map = 0   # (chapter, sentence_index) absent from sentence_uuid_map
    skipped_dedup = 0    # pair already written from an earlier overlapping chunk
    seen_pairs: set[tuple[str, str]] = set()

    with destination.open("w", encoding="utf-8") as fh:
        for chunk_id, chapter, merged_text in invocation_documents:
            try:
                response = invoke_json(
                    chat_model=chat_model,
                    system_prompt=system_prompt,
                    user_prompt=_build_user_prompt(chapter, chunk_id, merged_text),
                )
                log_invocation_metadata(response.invocation_metadata)
                print(f"User prompt:\n{_build_user_prompt(chapter, chunk_id, merged_text)}") # DEBUG; DO NOT REMOVE
                reasoning_content = response.thinking.reasoning_content or "" # DEBUG; DO NOT REMOVE
                print(f"Thinking:\n{(reasoning_content[:200])} ... {reasoning_content[-200:]}") # DEBUG; DO NOT REMOVE
                print(f"Response payload:\n{response.payload}") # DEBUG; DO NOT REMOVE
            except EmptyOllamaResponseError:
                skipped_blank += 1
                continue

            entities = _normalize_entities(response.payload, allowed_classifications)

            for surface_form, sentence_index, classification, reason in entities:
                src_uuid = sentence_uuid_map.get((chapter, sentence_index))
                if src_uuid is None:
                    print(
                        f"[WARN] No sentence mapping for "
                        f"(chapter={chapter}, sentence={sentence_index}) "
                        f"— surface_form={surface_form!r} chunk={chunk_id}"
                    )
                    skipped_no_map += 1
                    continue

                pair = (surface_form, src_uuid)
                if pair in seen_pairs:
                    skipped_dedup += 1
                    continue
                seen_pairs.add(pair)

                row = {
                    "surface_form": surface_form,
                    "classification": classification,
                    "reason": reason,
                    "src_uuid": src_uuid,
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1

            fh.flush()

    print(f"Source chunks:                       {len(chunk_documents)}")
    print(f"LLM invocations:                     {len(invocation_documents)}")
    print(f"Wrote mentions:                      {written}")
    print(f"Skipped — dedup (already written):   {skipped_dedup}")
    print(f"Skipped — no sentence map entry:     {skipped_no_map}")
    print(f"Skipped — blank model response:      {skipped_blank}")
    print(f"Output JSONL: {destination}")
    return destination


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract glycan structural terms from EOG Chroma chunks using Ollama."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help=(
            "Optional output JSONL path. "
            "Defaults to data/inputs/eog/term_mentions/eog_glycan_term_mentions.jsonl"
        ),
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help="Optional limit on the number of Chroma chunk documents to process.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract_eog_terms(output_path=args.output_path, max_documents=args.max_documents)
