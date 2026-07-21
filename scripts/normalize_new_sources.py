"""Normalize raw TSVs from newly-added glycan resources into terms.jsonl.

Output JSONL schema (matches existing src_*/terms.jsonl):

    {
      "term":      <surface form>,
      "xref":      "SRC:<UPPER_SNAKE_NAME>",
      "term_uuid": "GSD:<uuid5(name+xref)>",   # deterministic, stable
      "src_uuid":  "SRC:<uuid4()>",            # unique per (term, source) row
      "metadata": {
          "exact_synonyms": [...],
          "gtc_id":         [...],
          "raw_term":       "...",
          "iupac_condensed":"...",            # if available
          "description":    "...",            # if available
          "db_xref":        [...],
      }
    }

Adds NO calls to LLMs. Pure deterministic normalisation. Run once.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path("/Users/cyrusay/Desktop/github_repo/gsd_v3")
INPUTS = ROOT / "data" / "inputs"

NAMESPACE = uuid.UUID("12345678-1234-5678-1234-1234567890ab")  # stable seed

GTC_RE = re.compile(r"\bG\d{5}[A-Z]{2}\b")


def stable_term_uuid(term: str, xref: str) -> str:
    seed = f"{term.strip().lower()}|{xref}"
    return f"GSD:{uuid.uuid5(NAMESPACE, seed)}"


def fresh_src_uuid() -> str:
    return f"SRC:{uuid.uuid4()}"


def write_terms(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Per-source normalisers
# ---------------------------------------------------------------------------


def normalize_glycoepitope() -> int:
    src = INPUTS / "src_glycoepitope" / "raw" / "glycoepitope.tsv"
    xref = "SRC:GLYCOEPITOPE"
    rows: list[dict] = []
    seen_uuids: set[str] = set()
    with src.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            name = (r.get("Epitope Name") or "").strip()
            if not name:
                continue
            epitope_id = (r.get("Epitope ID") or "").strip()
            seq = (r.get("Epitope Sequence") or "").strip()
            # If name has "/ context" disambiguator (e.g. "O-Mannosyl Glycan / Yeast")
            # KEEP the full disambiguated name as the term — they are biologically
            # distinct glycans and should not collapse.
            primary = name
            aliases: list[str] = []
            term_uuid = stable_term_uuid(primary, xref)
            # If same primary still collides (true duplicate row), use epitope_id
            # as a second-key salt to keep it stable but unique.
            if term_uuid in seen_uuids:
                term_uuid = stable_term_uuid(primary + "|" + epitope_id, xref)
            seen_uuids.add(term_uuid)
            rows.append({
                "term": primary,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": aliases,
                    "iupac_condensed": seq or None,
                    "raw_term": name,
                    "db_xref": [f"GlycoEpitope:{epitope_id}"] if epitope_id else [],
                    "gtc_id": [],
                },
            })
    write_terms(INPUTS / "src_glycoepitope" / "terms.jsonl", rows)
    return len(rows)


def normalize_biooligo() -> int:
    src = INPUTS / "src_biooligo" / "raw" / "biooligo_glycans.tsv"
    xref = "SRC:BIOOLIGO"
    rows: list[dict] = []
    with src.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            seq = (r.get("sequence") or "").strip()
            category = (r.get("category") or "").strip()
            url = (r.get("detail_url") or "").strip()
            term_uuid = stable_term_uuid(name, xref)
            rows.append({
                "term": name,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": [],
                    "iupac_condensed": seq or None,
                    "raw_term": name,
                    "classification": category or None,
                    "db_xref": [url] if url else [],
                    "gtc_id": [],
                },
            })
    write_terms(INPUTS / "src_biooligo" / "terms.jsonl", rows)
    return len(rows)


def normalize_sugarbind() -> int:
    src = INPUTS / "src_sugarbind" / "raw" / "sugarbind_ligands.tsv"
    xref = "SRC:SUGARBIND"
    rows: list[dict] = []
    with src.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            label = (r.get("label") or "").strip()
            if not label:
                continue
            # SugarBind labels often look like:
            #   "Gangliotetraosylceramide (Asialo-GM1, GgO4, Gg4, GA1, Asialo-GM1a)"
            m = re.match(r"^(.*?)\s*\((.+)\)\s*$", label)
            if m:
                primary = m.group(1).strip()
                aliases = [a.strip() for a in m.group(2).split(",") if a.strip()]
            else:
                primary = label
                aliases = []

            syns_field = (r.get("ligand_synonyms") or "").strip()
            for syn in re.split(r"\s*\|\s*", syns_field):
                syn = syn.strip()
                if syn and syn not in aliases and syn != primary:
                    aliases.append(syn)

            gtc = (r.get("glycan_references:glytoucan") or "").strip()
            gtc_list = [g for g in re.split(r"\s*[|;,]\s*", gtc) if GTC_RE.match(g or "")]

            sb_id = (r.get("ligand_id") or "").strip()
            aglycon = (r.get("aglycon") or "").strip()
            glyco_type = (r.get("glycoconjugate_type") or "").strip()
            db_xref = []
            if sb_id:
                db_xref.append(f"SugarBind:{sb_id}")
            url = (r.get("url") or "").strip()
            if url:
                db_xref.append(url)

            term_uuid = stable_term_uuid(primary, xref)
            rows.append({
                "term": primary,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": aliases,
                    "gtc_id": gtc_list,
                    "raw_term": label,
                    "classification": glyco_type or None,
                    "description": f"Aglycon: {aglycon}" if aglycon else None,
                    "db_xref": db_xref,
                },
            })
    write_terms(INPUTS / "src_sugarbind" / "terms.jsonl", rows)
    return len(rows)


def normalize_cummings() -> int:
    src = INPUTS / "src_cummings" / "raw" / "determinants_cummings.tsv"
    xref = "SRC:CUMMINGS"
    rows: list[dict] = []
    with src.open(encoding="utf-8") as f:
        # The file's first line is a sentence-style header, so use DictReader anyway
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        seen = set()
        for r in reader:
            if len(r) < 2:
                continue
            seq = r[0].strip()
            name = r[1].strip()
            if not name:
                continue
            # the trivial name often has parenthetical alternates: 'Type 2 LN (N-acetyllactosamine)'
            m = re.match(r"^(.*?)\s*\((.+)\)\s*$", name)
            if m:
                primary = m.group(1).strip().strip(' "')
                aliases = [a.strip().strip('"') for a in m.group(2).split(",") if a.strip()]
            else:
                primary = name.strip().strip(' "')
                aliases = []
            # de-quote curly quotes
            primary = primary.replace("“", "").replace("”", "").strip()
            aliases = [a.replace("“", "").replace("”", "").strip() for a in aliases]

            if not primary:
                continue
            key = primary.lower()
            if key in seen:
                continue
            seen.add(key)

            term_uuid = stable_term_uuid(primary, xref)
            rows.append({
                "term": primary,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": aliases,
                    "iupac_condensed": seq or None,
                    "raw_term": name,
                    "db_xref": [],
                    "gtc_id": [],
                },
            })
    write_terms(INPUTS / "src_cummings" / "terms.jsonl", rows)
    return len(rows)


def _pubdict_to_jsonl(src_dir: Path, tsv_name: str, xref: str) -> int:
    src = src_dir / "raw" / tsv_name
    if not src.exists():
        print(f"  [SKIP] missing: {src}")
        return 0

    rows: list[dict] = []
    seen = {}  # term -> row index (to merge gtc_ids when same name appears twice)
    with src.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for r in reader:
            if not r:
                continue
            if r[0].startswith("#"):
                # might be a header; strip the '#' and continue
                continue
            if len(r) < 2:
                continue
            label = r[0].strip().strip('"')
            url = r[1].strip()
            if not label:
                continue
            # extract GTC accession from URL
            m = GTC_RE.search(url)
            gtc = [m.group(0)] if m else []

            key = label.lower()
            if key in seen:
                existing = rows[seen[key]]
                for g in gtc:
                    if g not in existing["metadata"]["gtc_id"]:
                        existing["metadata"]["gtc_id"].append(g)
                continue
            seen[key] = len(rows)

            term_uuid = stable_term_uuid(label, xref)
            rows.append({
                "term": label,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": [],
                    "gtc_id": gtc,
                    "raw_term": label,
                    "db_xref": [url] if url else [],
                },
            })
    write_terms(src_dir / "terms.jsonl", rows)
    return len(rows)


def normalize_pubdict_glycan_motif() -> int:
    return _pubdict_to_jsonl(
        INPUTS / "src_pubdict-glycan-motif",
        "pubdictionaries-glycan-motif.tsv",
        "SRC:PUBDICT_GLYCAN_MOTIF",
    )


def normalize_pubdict_glycosmos() -> int:
    return _pubdict_to_jsonl(
        INPUTS / "src_pubdict-glycosmos",
        "glycan-GlyCosmos.tsv",
        "SRC:PUBDICT_GLYCOSMOS",
    )


def normalize_pubdict_motifglytoucan() -> int:
    return _pubdict_to_jsonl(
        INPUTS / "src_pubdict-motifglytoucan",
        "motifGlyTouCanID.tsv",
        "SRC:PUBDICT_MOTIF_GTC",
    )


# ---------------------------------------------------------------------------
# Scraped-source normalisers (best effort; tolerate missing files)
# ---------------------------------------------------------------------------


def _glycomotif_to_jsonl(src_dir: Path, xref: str) -> int:
    """Generic normaliser for the scraped GlycoMotif TSVs.

    Schemas supported:
      * v1 (original scrape):  id, label, glytoucan_id, aliases (mixed), url
      * v2 (re-scrape):        id, label, glytoucan_id, names, keywords, url
                               + optional bgsl_curator_meta (carried via xlsx round-trip)

    Selection rule: if a `*_v2.tsv` file is present, use ONLY that file (the
    v1 `aliases` column mixed names with classification keywords like
    "LacNAc", "Glycolipid", which polluted exact_synonyms downstream). When
    only v1 is present, fall back to reading `aliases`.

    Output columns from v2:
      * exact_synonyms  ← `names` (the actual alternative names)
      * keywords        ← `keywords` (categorical descriptors; NEVER synonyms)
    """
    raw_dir = src_dir / "raw"
    if not raw_dir.exists():
        print(f"  [SKIP] missing: {raw_dir}")
        return 0

    all_tsvs = sorted(raw_dir.glob("*.tsv"))
    v2_tsvs = [t for t in all_tsvs if t.stem.endswith("_v2")]
    tsvs = v2_tsvs if v2_tsvs else all_tsvs
    if not tsvs:
        print(f"  [SKIP] no TSV in {raw_dir}")
        return 0

    rows: list[dict] = []
    seen = {}
    for tsv in tsvs:
        is_v2 = tsv.stem.endswith("_v2")
        with tsv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for r in reader:
                label = (r.get("label") or r.get("name") or "").strip()
                if not label:
                    continue
                gtc_raw = (r.get("glytoucan_id") or r.get("gtc_id") or "").strip()
                gtc = [g.strip() for g in re.split(r"\s*[|;,]\s*", gtc_raw) if GTC_RE.match(g.strip())]

                # v2: synonyms from `names`; keywords kept as a separate field.
                # v1: synonyms from `aliases` (legacy fallback).
                if is_v2:
                    names_raw = (r.get("names") or "").strip()
                    keywords_raw = (r.get("keywords") or "").strip()
                    aliases = [a.strip() for a in re.split(r"\s*\|\s*", names_raw) if a.strip()]
                    keywords = [k.strip() for k in re.split(r"\s*\|\s*", keywords_raw) if k.strip()]
                else:
                    aliases_raw = (r.get("aliases") or r.get("synonyms") or "").strip()
                    aliases = [a.strip() for a in re.split(r"\s*\|\s*", aliases_raw) if a.strip()]
                    keywords = []
                url = (r.get("url") or "").strip()
                motif_id = (r.get("id") or "").strip()

                key = label.lower()
                if key in seen:
                    existing = rows[seen[key]]
                    for g in gtc:
                        if g not in existing["metadata"]["gtc_id"]:
                            existing["metadata"]["gtc_id"].append(g)
                    for a in aliases:
                        if a not in existing["metadata"]["exact_synonyms"]:
                            existing["metadata"]["exact_synonyms"].append(a)
                    if keywords:
                        existing_kw = existing["metadata"].setdefault("keywords", [])
                        for k in keywords:
                            if k not in existing_kw:
                                existing_kw.append(k)
                    continue
                seen[key] = len(rows)

                db_xref = []
                if motif_id:
                    db_xref.append(f"GlycoMotif:{motif_id}")
                if url:
                    db_xref.append(url)

                md = {
                    "exact_synonyms": aliases,
                    "gtc_id": gtc,
                    "raw_term": label,
                    "db_xref": db_xref,
                }
                if keywords:
                    md["keywords"] = keywords
                rows.append({
                    "term": label,
                    "xref": xref,
                    "term_uuid": stable_term_uuid(label, xref),
                    "src_uuid": fresh_src_uuid(),
                    "metadata": md,
                })
    write_terms(src_dir / "terms.jsonl", rows)
    return len(rows)


def normalize_glycomotif_ggm() -> int:
    return _glycomotif_to_jsonl(INPUTS / "src_glycomotif_ggm", "SRC:GLYCOMOTIF_GGM")


def normalize_glycomotif_gdv() -> int:
    return _glycomotif_to_jsonl(INPUTS / "src_glycomotif_gdv", "SRC:GLYCOMOTIF_GDV")


def normalize_glycomotif_ccrc() -> int:
    return _glycomotif_to_jsonl(INPUTS / "src_glycomotif_ccrc", "SRC:GLYCOMOTIF_CCRC")


_MOJIBAKE_FIXES = {
    "Î±": "α",
    "Î²": "β",
    "Î³": "γ",
    "Î´": "δ",
    "â€™": "'",
    "â€“": "–",
    "â€”": "—",
}


def _fix_mojibake(s: str) -> str:
    for bad, good in _MOJIBAKE_FIXES.items():
        s = s.replace(bad, good)
    return s


def _glyconavi_pubdict_to_jsonl(src_dir: Path, tsv_name: str, xref: str) -> int:
    """Pubdictionaries glyconavi-* TSVs use columns: id (URL), label."""
    src = src_dir / "raw" / tsv_name
    if not src.exists():
        print(f"  [SKIP] missing: {src}")
        return 0
    rows: list[dict] = []
    seen = {}
    with src.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)  # id, label
        for r in reader:
            if len(r) < 2:
                continue
            url = r[0].strip()
            label = _fix_mojibake(r[1].strip().strip('"'))
            if not label:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen[key] = True

            rows.append({
                "term": label,
                "xref": xref,
                "term_uuid": stable_term_uuid(label, xref),
                "src_uuid": fresh_src_uuid(),
                "metadata": {
                    "exact_synonyms": [],
                    "gtc_id": [],
                    "raw_term": label,
                    "db_xref": [url] if url else [],
                },
            })
    write_terms(src_dir / "terms.jsonl", rows)
    return len(rows)


def normalize_pubdict_glyconavi_name() -> int:
    return _glyconavi_pubdict_to_jsonl(
        INPUTS / "src_pubdict-glyconavi-name",
        "glyconavi-glycan-name.tsv",
        "SRC:PUBDICT_GLYCONAVI_NAME",
    )


def normalize_pubdict_glyconavi_abbrev() -> int:
    return _glyconavi_pubdict_to_jsonl(
        INPUTS / "src_pubdict-glyconavi-abbrev",
        "glyconavi-glycan-abbreviation.tsv",
        "SRC:PUBDICT_GLYCONAVI_ABBREV",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    normalisers = [
        ("glycoepitope",            normalize_glycoepitope),
        ("biooligo",                normalize_biooligo),
        ("sugarbind",               normalize_sugarbind),
        ("cummings",                normalize_cummings),
        ("pubdict-glycan-motif",    normalize_pubdict_glycan_motif),
        ("pubdict-glycosmos",       normalize_pubdict_glycosmos),
        ("pubdict-motifglytoucan",  normalize_pubdict_motifglytoucan),
        ("glycomotif-ggm",          normalize_glycomotif_ggm),
        ("glycomotif-gdv",          normalize_glycomotif_gdv),
        ("glycomotif-ccrc",         normalize_glycomotif_ccrc),
        ("pubdict-glyconavi-name",  normalize_pubdict_glyconavi_name),
        ("pubdict-glyconavi-abbrev", normalize_pubdict_glyconavi_abbrev),
    ]

    print("=" * 70)
    print("Normalising raw sources -> terms.jsonl")
    print("=" * 70)
    for label, fn in normalisers:
        try:
            n = fn()
            print(f"  [{label:30s}]  {n:>5d} terms")
        except FileNotFoundError as e:
            print(f"  [{label:30s}]  SKIP ({e.filename})")
        except Exception as e:
            print(f"  [{label:30s}]  ERROR: {e}")
    print("=" * 70)


if __name__ == "__main__":
    main()
