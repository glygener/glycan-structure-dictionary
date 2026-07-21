"""Build a flat reviewer TSV from the gsd_v2.0.0-draft master_nodes.

One row per node. Columns (in this exact order):

  term, exact_synonyms, abbreviations, broad_synonyms, narrow_synonyms,
  related_synonyms, classification, gtc_id, gsd_id, glycomotif_id, sources,
  eog_sentence

The TSV is sorted by 3-tier classification (1A < 1B < 1C < 2A … < 3C < X
< Unclassified), with `lbl` as the within-class tiebreaker.

`eog_sentence` is the first sentence of the highest-scoring EoG textbook
chunk whose text contains the node's primary `lbl` as a case-insensitive
substring (false-match guard). Empty if no hit clears the substring check.

Outputs:
  data/outputs/releases/gsd_v2.0.0-draft/bGSL_v2.0.0_review.tsv
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
RELEASE_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft"

# Make the resolver tools package importable for the EoG store.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "gsd" / "part2_enrichment" / "1_ai-assisted_term_matching"))


# ---------------------------------------------------------------------------
# Classification sort order
# ---------------------------------------------------------------------------

CLASS_ORDER = [
    "1A", "1B", "1C",
    "2A", "2B", "2C", "2D", "2E",
    "3A", "3B", "3C",
    "X",
]
CLASS_SORT_KEY = {c: i for i, c in enumerate(CLASS_ORDER)}


def class_sort_value(class_code: str | None) -> tuple[int, str]:
    """Return (bucket_index, class_code) — unknown / blank go last."""
    if not class_code:
        return (len(CLASS_ORDER) + 1, "")
    return (CLASS_SORT_KEY.get(class_code, len(CLASS_ORDER)), class_code)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def latest(glob_pattern: str) -> Path:
    matches = sorted(glob.glob(glob_pattern))
    if not matches:
        raise FileNotFoundError(f"No file matches {glob_pattern}")
    return Path(matches[-1])


def load_master_nodes() -> list[dict]:
    p = latest(str(RELEASE_DIR / "master_nodes_*.json"))
    print(f"[load] master_nodes: {p.name}")
    return json.loads(p.read_text())


def load_master_edges() -> list[dict]:
    p = latest(str(RELEASE_DIR / "master_edges_*.json"))
    print(f"[load] master_edges: {p.name}")
    return json.loads(p.read_text())


def load_term_class() -> dict[str, str]:
    """Return {term_uuid: class_code}.

    The classify_terms.py output pads cells with whitespace for visual
    column alignment, so we strip both header keys and cell values.
    """
    p = RELEASE_DIR / "classification" / "term_class.tsv"
    if not p.exists():
        print(f"[warn] No classification file at {p}")
        return {}
    out: dict[str, str] = {}
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        # Strip whitespace from fieldnames so .get('term_uuid') works.
        reader.fieldnames = [(c or "").strip() for c in (reader.fieldnames or [])]
        for row in reader:
            uid = (row.get("term_uuid") or "").strip()
            cls = (row.get("class_code") or "").strip()
            if uid:
                out[uid] = cls
    print(f"[load] term_class: {len(out)} entries")
    return out


# ---------------------------------------------------------------------------
# Edge-driven synonym lookups
# ---------------------------------------------------------------------------


_CURATOR_COMMENT_RX = re.compile(
    r"^curator-hint:\s*.+?\s+(broad_synonym_of|narrow_synonym_of|related_synonym_of|exact_synonym_of|abbreviation_of|is_a)\s+(.+)$"
)


def _target_label_for_edge(edge: dict, uuid_to_lbl: dict[str, str]) -> str | None:
    """Resolve the object label for an edge.

    Prefer the master_nodes lbl. For curator-hint edges where `obj` is a stub
    (lives only in Chroma, not in master_nodes), fall back to parsing the
    target label out of the comment string.
    """
    obj = edge.get("obj") or ""
    if obj in uuid_to_lbl:
        return uuid_to_lbl[obj]
    comment = (edge.get("comment") or "").strip()
    if comment:
        m = _CURATOR_COMMENT_RX.match(comment)
        if m:
            return m.group(2).strip().rstrip(".").strip()
    return None


def build_edge_indexes(edges: list[dict], uuid_to_lbl: dict[str, str]) -> tuple[
    dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]
]:
    """Return (broad_of, narrow_of, related_of) keyed by term_uuid.

    broad_of[u]   = labels v such that (u, broad_synonym_of,   v) ∈ edges
    narrow_of[u]  = labels v such that (u, narrow_synonym_of,  v) ∈ edges
    related_of[u] = labels v such that (u, related_synonym_of, v) OR
                                       (v, related_synonym_of, u) ∈ edges

    Stub-target edges (obj_uuid lives only in Chroma) have their target
    label parsed out of the comment string instead.
    """
    broad: dict[str, list[str]] = {}
    narrow: dict[str, list[str]] = {}
    related: dict[str, list[str]] = {}

    for e in edges:
        pred = e.get("pred") or ""
        subj = e.get("subj") or ""
        obj = e.get("obj") or ""
        subj_lbl = uuid_to_lbl.get(subj)
        if not subj_lbl:
            continue
        obj_lbl = _target_label_for_edge(e, uuid_to_lbl)
        if not obj_lbl:
            continue
        # Was obj a real node (we can build the reverse-direction edge)?
        obj_was_real = obj in uuid_to_lbl

        if pred == "broad_synonym_of":
            broad.setdefault(subj, []).append(obj_lbl)
        elif pred == "narrow_synonym_of":
            narrow.setdefault(subj, []).append(obj_lbl)
        elif pred in ("related_synonym_of", "has_related_synonym"):
            related.setdefault(subj, []).append(obj_lbl)
            # Reverse direction (related is symmetric) only if obj is real;
            # otherwise we don't know which subj_uuid to attach this to.
            if obj_was_real:
                related.setdefault(obj, []).append(subj_lbl)

    # Dedup preserve-order
    for d in (broad, narrow, related):
        for k in list(d.keys()):
            seen = set()
            kept = []
            for x in d[k]:
                if x not in seen:
                    seen.add(x)
                    kept.append(x)
            d[k] = kept

    return broad, narrow, related


# ---------------------------------------------------------------------------
# EoG textbook sentence lookup
# ---------------------------------------------------------------------------


def _get_eog_store():
    """Lazy-load the EoG Chroma store via the resolver tools module."""
    from tools import _get_eog_store as _impl  # type: ignore
    return _impl()


_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(\[])")


def first_sentence_with_term(text: str, term: str) -> str | None:
    """Return the first sentence in `text` that contains `term` (case-insensitive),
    cleaned of EoG sentence tags. None if no sentence matches.
    """
    if not text or not term:
        return None
    # Strip <S:n>...</S:n> tags
    cleaned = re.sub(r"</?S:\d+>", "", text).strip()
    if not cleaned:
        return None
    # Split into sentences
    sentences = _SENT_END.split(cleaned)
    lowered = term.lower()
    for sent in sentences:
        if lowered in sent.lower():
            sent = sent.strip()
            if sent:
                return sent
    return None


def query_eog_sentence(store, term: str, alt_terms: list[str] | None = None) -> str:
    """Return one EoG-textbook sentence that mentions `term` (or any of
    `alt_terms`), else empty string.

    Strategy:
      1. Vector-search using the primary term.
      2. Walk the top-k chunks looking for a sentence containing `term` as a
         case-insensitive substring (false-match guard).
      3. If nothing matched, try each `alt_term` in turn (abbreviations,
         exact-synonyms): vector-search using the alt term, then check if
         any returned sentence contains either the alt or the primary term.
    """
    candidates: list[str] = []
    if term:
        candidates.append(term)
    if alt_terms:
        for a in alt_terms:
            if a and a not in candidates:
                candidates.append(a)

    for q in candidates:
        try:
            results = store.similarity_search_with_relevance_scores(
                query=q, k=4, score_threshold=0.15,
            )
        except Exception as exc:
            print(f"  [eog] {q!r}: {exc}", file=sys.stderr)
            continue
        if not results:
            continue
        for doc, _score in results:
            # Try matching against ANY of the candidate terms inside the chunk.
            for needle in candidates:
                sent = first_sentence_with_term(doc.page_content, needle)
                if sent:
                    if len(sent) > 400:
                        sent = sent[:400].rstrip() + "..."
                    return sent
    return ""


# ---------------------------------------------------------------------------
# Column extractors
# ---------------------------------------------------------------------------


def glycomotif_id_from_db_xref(db_xref) -> str:
    """Extract GlycoMotif: prefixed entries from a db_xref field."""
    if not db_xref:
        return ""
    if isinstance(db_xref, str):
        items = [db_xref]
    else:
        items = list(db_xref)
    found = []
    for x in items:
        if not isinstance(x, str):
            continue
        if x.startswith("GlycoMotif:"):
            found.append(x)
        elif re.match(r"^(GGM|CCRC|GDV)\.\d", x):
            # Defensive: bare GGM.000001 → prepend the namespace
            found.append(f"GlycoMotif:{x}")
    # Dedup preserve-order
    seen = set()
    return "; ".join(x for x in found if not (x in seen or seen.add(x)))


def source_summary(sources: list) -> str:
    """Return `; `-joined unique src codes (with SRC: prefix stripped)."""
    if not sources:
        return ""
    seen = set()
    out = []
    for s in sources:
        src = (s.get("src") or "").strip()
        if not src:
            continue
        short = src[len("SRC:"):] if src.startswith("SRC:") else src
        if short not in seen:
            seen.add(short)
            out.append(short)
    return "; ".join(out)


# ---------------------------------------------------------------------------
# EoG sentence cache (preserve already-fetched sentences)
# ---------------------------------------------------------------------------


EOG_CACHE_PATH = RELEASE_DIR / "bGSL_eog_cache.json"


def load_eog_cache(sidecar: Path, out_path: Path, nodes: list[dict]) -> dict[str, str]:
    """Return {term_uuid: eog_sentence} of already-vetted sentences.

    Keyed by term_uuid so a sentence is preserved EXACTLY per node — it
    survives a relabel/merge (same UUID) and is never borrowed by a different
    node. Split children get fresh UUIDs, so they start blank (no new sentence
    is invented) unless --refresh-eog is passed.

    If the sidecar is absent (first run after this change), bootstrap it from
    the existing TSV by matching each node's current label.
    """
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text())
        except json.JSONDecodeError:
            pass
    cache: dict[str, str] = {}
    if not out_path.exists():
        return cache
    by_label: dict[str, str] = {}
    with out_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sent = (row.get("eog_sentence") or "").strip()
            term = (row.get("term") or "").strip().lower()
            if sent and term:
                by_label[term] = sent
    for n in nodes:
        uid = n.get("term_uuid")
        lbl = (n.get("lbl") or "").strip().lower()
        if uid and lbl in by_label:
            cache[uid] = by_label[lbl]
    return cache


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--refresh-eog", action="store_true",
        help="Re-query the EoG embedding store for nodes with no cached "
             "sentence (makes OpenAI calls). Default: preserve existing "
             "sentences only, no API calls.",
    )
    args = ap.parse_args()

    nodes = load_master_nodes()
    edges = load_master_edges()
    cls_map = load_term_class()

    uuid_to_lbl = {n.get("term_uuid"): n.get("lbl") for n in nodes if n.get("term_uuid")}
    broad_of, narrow_of, related_of = build_edge_indexes(edges, uuid_to_lbl)

    out_path = RELEASE_DIR / "bGSL_v2.0.0_review.tsv"
    eog_cache = load_eog_cache(EOG_CACHE_PATH, out_path, nodes)
    print(f"[eog] preserved sentence cache: {len(eog_cache)} entries (keyed by term_uuid)"
          + ("" if args.refresh_eog else "  — no new sentences fetched; pass --refresh-eog to query the store"))

    eog_store = None
    if args.refresh_eog:
        print("[init] loading EoG store (refresh mode)...")
        eog_store = _get_eog_store()
        print("[init] EoG store ready")

    # Build rows
    n_preserved = 0
    n_fetched = 0
    rows: list[dict] = []
    for i, n in enumerate(nodes, start=1):
        uid = n.get("term_uuid", "")
        lbl = n.get("lbl") or ""
        if i % 100 == 0 or i == 1:
            print(f"  [{i}/{len(nodes)}] {lbl[:60]}")

        cls = n.get("classification") or cls_map.get(uid, "")
        exact = n.get("exact_synonyms") or []
        abbrev = n.get("abbreviations") or []
        broad = broad_of.get(uid, [])
        narrow = narrow_of.get(uid, [])
        related = related_of.get(uid, [])
        gtc = n.get("gtc_id") or []
        gsd = n.get("gsd_id") or ""
        gmid = glycomotif_id_from_db_xref(n.get("db_xref"))
        srcs = source_summary(n.get("sources") or [])

        # 1) Preserve this node's already-vetted sentence (by UUID, no API call).
        eog = eog_cache.get(uid, "")
        if eog:
            n_preserved += 1
        # 2) Only in --refresh-eog mode, query the store for genuine misses.
        elif args.refresh_eog and eog_store and lbl:
            alt_terms = (abbrev or []) + (exact or [])
            eog = query_eog_sentence(eog_store, lbl, alt_terms=alt_terms)
            if eog:
                n_fetched += 1

        rows.append({
            "_uuid": uid,
            "_class_sort": class_sort_value(cls),
            "_lbl_sort": lbl.lower(),
            "bgsl_id": uid,   # carry the term_uuid (GSD:…) over verbatim as the bGSL id
            "term": lbl,
            "exact_synonyms": "; ".join(exact),
            "abbreviations": "; ".join(abbrev),
            "broad_synonyms": "; ".join(broad),
            "narrow_synonyms": "; ".join(narrow),
            "related_synonyms": "; ".join(related),
            "classification": cls,
            "gtc_id": "; ".join(gtc) if isinstance(gtc, list) else str(gtc or ""),
            "gsd_id": gsd if isinstance(gsd, str) else "",
            "glycomotif_id": gmid,
            "sources": srcs,
            "eog_sentence": eog,
        })

    rows.sort(key=lambda r: (r["_class_sort"], r["_lbl_sort"]))

    fieldnames = [
        "bgsl_id", "term", "exact_synonyms", "abbreviations",
        "broad_synonyms", "narrow_synonyms", "related_synonyms",
        "classification", "gtc_id", "gsd_id", "glycomotif_id",
        "sources", "eog_sentence",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=fieldnames, delimiter="\t",
            quoting=csv.QUOTE_MINIMAL, lineterminator="\n",
        )
        w.writeheader()
        for r in rows:
            # Drop the private sort keys
            w.writerow({k: r.get(k, "") for k in fieldnames})

    # Persist the UUID-keyed sentence cache so the next run preserves these
    # exact sentences (survives relabel/merge; never reassigned to other nodes).
    new_cache = {r["_uuid"]: r["eog_sentence"] for r in rows if r.get("_uuid") and r["eog_sentence"]}
    EOG_CACHE_PATH.write_text(json.dumps(new_cache, ensure_ascii=False, indent=2), encoding="utf-8")

    # Quick stats
    n_with_class = sum(1 for r in rows if r["classification"])
    n_with_eog = sum(1 for r in rows if r["eog_sentence"])
    n_with_gmid = sum(1 for r in rows if r["glycomotif_id"])
    n_with_gsd = sum(1 for r in rows if r["gsd_id"])
    print(f"\n[done] {len(rows)} rows → {out_path}")
    print(f"  with classification : {n_with_class}")
    print(f"  with EoG sentence   : {n_with_eog}  (preserved {n_preserved}, newly fetched {n_fetched})")
    print(f"  with glycomotif_id  : {n_with_gmid}")
    print(f"  with gsd_id         : {n_with_gsd}")


if __name__ == "__main__":
    main()
