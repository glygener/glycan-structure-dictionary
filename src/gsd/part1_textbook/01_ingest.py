from __future__ import annotations

# Ingest EOG chapters into indexed sentence JSONL and a chunked Chroma vector store.

import json
import re
import sys
import uuid
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

from gsd.adapters.chroma import build_chroma_from_documents
from gsd.config import (
    load_chroma_config,
    load_models_config,
    load_ollama_config,
    load_paths_config,
)

HEADER_TEXT = (
    "NCBI Bookshelf. A service of the National Library of Medicine, National Institutes "
    "of Health. Varki A, Cummings RD, Esko JD, et al., editors. Essentials of "
    "Glycobiology [Internet]. 4th edition. Cold Spring Harbor (NY): Cold Spring Harbor "
    "Laboratory Press; 2022.  doi: 10.1101/glycobiology.4e."
) # This appears at the start of every chapter. Removing it because it adds noise to the RAG retrieval. 
  # Proper citation could be found at data/inputs/eog/indexed_sentences/eog_sentence_map.md

URL_FULL_RE = re.compile(r"^(?:https?|ftp)://\S+$", re.IGNORECASE)

ABBREV_TOKENS = {
    "e.g.",
    "i.e.",
    "vs.",
    "Fig.",
    "Figs.",
    "Dr.",
    "Mr.",
    "Ms.",
    "Mrs.",
    "Prof.",
    "al.",
    "et al.",
    "No.",
    "Eq.",
    "Eqs.",
    "Ref.",
    "Refs.",
    "Inc.",
    "Co.",
    "Jr.",
    "Sr.",
    "St.",
    "Ch.",
    "Jan.",
    "Feb.",
    "Mar.",
    "Apr.",
    "Jun.",
    "Jul.",
    "Aug.",
    "Sep.",
    "Sept.",
    "Oct.",
    "Nov.",
    "Dec.",
    "(Fig.",
    "(e.g.",
    "(i.e.",
}

ABBREV_TOKENS_LOWER = {token.lower() for token in ABBREV_TOKENS}
CHAPTER_FILE_RE = re.compile(r"^chapter_(\d+)\.txt$", re.IGNORECASE)
HEADER_TEXT_NORMALIZED = re.sub(r"\s+", " ", HEADER_TEXT).strip()
SENTENCE_PUNCT = {".", "!", "?"}
CLOSING_CHARS = set("\"'”’)]}")


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def strip_known_header(text: str) -> str:
    """Remove the shared NCBI Bookshelf prefix if present."""
    normalized = normalize_whitespace(text)
    if normalized.startswith(HEADER_TEXT_NORMALIZED):
        return normalized[len(HEADER_TEXT_NORMALIZED) :].strip()
    return normalized


def parse_chapter_number(path: Path) -> int:
    """Extract chapter number from chapter_NN.txt filename."""
    match = CHAPTER_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unsupported chapter filename format: {path.name}")
    return int(match.group(1))


def _extract_tokens(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _is_abbreviation(tokens: list[str]) -> bool:
    if not tokens:
        return False

    last_token = tokens[-1].rstrip("\"'”’)]}")
    if last_token in ABBREV_TOKENS or last_token.lower() in ABBREV_TOKENS_LOWER:
        return True
    if URL_FULL_RE.match(last_token):
        return True
    if re.fullmatch(r"[A-Za-z]\.", last_token):
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", last_token):
        return True

    if len(tokens) >= 2:
        pair = f"{tokens[-2]} {last_token}"
        if pair in ABBREV_TOKENS or pair.lower() in ABBREV_TOKENS_LOWER:
            return True

    return False


def _looks_like_decimal(text: str, index: int) -> bool:
    if text[index] != ".":
        return False
    left = text[index - 1] if index > 0 else ""
    right = text[index + 1] if index + 1 < len(text) else ""
    return left.isdigit() and right.isdigit()


def split_sentences_conservative(text: str) -> list[str]:
    """Split text conservatively into sentences."""
    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    sentences: list[str] = []
    start = 0

    for i, char in enumerate(normalized):
        if char not in SENTENCE_PUNCT:
            continue
        if _looks_like_decimal(normalized, i):
            continue

        window = normalized[start : i + 1]
        if _is_abbreviation(_extract_tokens(window)):
            continue

        cursor = i + 1
        while cursor < len(normalized) and normalized[cursor] in CLOSING_CHARS:
            cursor += 1
        while cursor < len(normalized) and normalized[cursor].isspace():
            cursor += 1

        if cursor >= len(normalized):
            sentence = normalized[start:].strip()
            if sentence:
                sentences.append(sentence)
            start = len(normalized)
            break

        next_char = normalized[cursor]
        if next_char.isupper() or next_char.isdigit() or next_char in "\"'([{":
            sentence = normalized[start:cursor].strip()
            if sentence:
                sentences.append(sentence)
            start = cursor

    if start < len(normalized):
        sentence = normalized[start:].strip()
        if sentence:
            sentences.append(sentence)

    return sentences


def build_tagged_chapter_text(sentences: list[str]) -> str:
    """Build a chapter string where each sentence is wrapped in sentence tags."""
    return "".join(
        f"<S:{index}>{sentence} </S:{index}>"
        for index, sentence in enumerate(sentences, start=1)
    )


def iter_chapter_files(input_dir: Path) -> list[Path]:
    """Return sorted chapter_*.txt files from input directory."""
    files = [
        path
        for path in input_dir.glob("chapter_*.txt")
        if path.is_file() and CHAPTER_FILE_RE.match(path.name)
    ]
    return sorted(files)


def write_sentence_index_jsonl(
    chapter_rows: list[tuple[int, list[str]]], output_jsonl: Path
) -> int:
    """Write one JSON object per sentence to a single JSONL map file."""
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for chapter, sentences in chapter_rows:
            for index, sentence in enumerate(sentences, start=1):
                row = {
                    "chapter": chapter,
                    "index": index,
                    "sentence": sentence,
                    "src_uuid": f"EOG:{uuid.uuid4()}",
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1
    return total


def ingest_eog_textbook() -> None:
    """Ingest raw chapter text into indexed sentence JSONL and EOG chunk vector store."""
    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()
    models_cfg = load_models_config()
    ollama_cfg = load_ollama_config()

    raw_chapter_dir = paths_cfg["resources"]["eog"]["raw_chapters"]
    indexed_sentences_dir = paths_cfg["resources"]["eog"]["indexed_sentences"]
    indexed_jsonl_path = indexed_sentences_dir / "eog_sentence_map.jsonl"

    eog_chroma_cfg = chroma_cfg["eog"]
    persist_directory = Path(eog_chroma_cfg["persist_directory"]).resolve()
    collection_name = eog_chroma_cfg["collection_name"]

    embedding_model = models_cfg["ollama"]["embedding_model"]["model"]
    ollama_host = ollama_cfg["host"]

    chapter_files = iter_chapter_files(raw_chapter_dir)
    if not chapter_files:
        raise FileNotFoundError(f"No chapter_*.txt files found in {raw_chapter_dir}")

    chapter_sentence_rows: list[tuple[int, list[str]]] = []
    raw_docs: list[Document] = []

    for chapter_file in chapter_files:
        chapter_number = parse_chapter_number(chapter_file)
        chapter_id = chapter_file.stem
        raw_text = chapter_file.read_text(encoding="utf-8")
        body_text = strip_known_header(raw_text)
        sentences = split_sentences_conservative(body_text)
        if not sentences:
            continue

        chapter_sentence_rows.append((chapter_number, sentences))
        raw_docs.append(
            Document(
                page_content=build_tagged_chapter_text(sentences),
                metadata={"chapter": chapter_number, "chapter_id": chapter_id},
            )
        )

    sentence_count = write_sentence_index_jsonl(chapter_sentence_rows, indexed_jsonl_path)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            r"</S:\d+>\s*(?=<S:\d+>)",
            r"\n\n",
            r"\n",
            r" ",
        ],
        keep_separator="end",
        is_separator_regex=True,
    )
    chunks = text_splitter.split_documents(raw_docs)

    chunk_ids: list[str] = []
    for chunk in chunks:
        chunk_id = f"EOG_CHUNK:{uuid.uuid4()}"
        chunk.metadata["id"] = chunk_id
        chunk_ids.append(chunk_id)

    build_chroma_from_documents(
        chunks,
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_model=embedding_model,
        ollama_host=ollama_host,
        ids=chunk_ids,
    )

    print(f"Loaded chapters: {len(chapter_files)}")
    print(f"Indexed sentences: {sentence_count}")
    print(f"Wrote sentence map: {indexed_jsonl_path}")
    print(f"Built chunks: {len(chunks)}")
    print(f"Persisted vector store: {persist_directory} (collection={collection_name})")


if __name__ == "__main__":
    ingest_eog_textbook()
