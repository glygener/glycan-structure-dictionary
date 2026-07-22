"""Classify glycan terms against the bGSL v3.0.0 3-tier scheme.

Pipeline (per term):

  Stage 0 (deterministic regex): catch 2A / 2D / 2E / 1C polymers without LLM.
  Stage 1 (LLM, gpt-oss:20b low-reasoning, JSON-schema constrained):
      single decision-tree prompt that walks Check 1 (3C) → Check 9 (X) and
      returns one of 12 classes.
  Stage 2a (LLM, only when Stage 1 returned 2B): 2B-vs-{1A,1B,2A,2C} re-check.
      Targets the user-reported false-2B failure mode.
  Stage 2b (LLM, only when Stage 1 returned 3A or X): 3C recall check.
      Targets the user-reported missed-3C failure mode.

Output:
  data/outputs/releases/gsd_v2.0.0-draft/classification/term_class.tsv
  data/outputs/releases/gsd_v2.0.0-draft/classification/classify_audit.jsonl

The input is the *pre-deduplication* master node list, so each row is one
resolver-assigned canonical surface form. The output is a stable lookup
table keyed by `term_uuid` AND `lbl` — a future dictionary rebuild can join
on either.

Usage:
    python scripts/classify_terms.py [--limit N] [--start N] [--no-llm]
                                     [--skip-stage-2]

Designed to be re-runnable: rows already present in term_class.tsv (matched
by term_uuid) are skipped unless --force is supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from gsd.adapters.ollama import (  # noqa: E402
    EmptyOllamaResponseError,
    build_chat_ollama,
    invoke_json,
    log_invocation_metadata,
)

INPUT_NODES = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft" / "review" / "master_nodes_prededuplication.json"
OUT_DIR = ROOT / "data" / "outputs" / "releases" / "gsd_v2.0.0-draft" / "classification"
OUT_TSV = OUT_DIR / "term_class.tsv"
OUT_AUDIT = OUT_DIR / "classify_audit.jsonl"

PROMPT_DIR = ROOT / "configs" / "prompts" / "classification"
SYS_PROMPT_MAIN = (PROMPT_DIR / "bgsl_classify_v3.md").read_text()
SYS_PROMPT_2B = (PROMPT_DIR / "bgsl_classify_v3_2b_check.md").read_text()
SYS_PROMPT_3C = (PROMPT_DIR / "bgsl_classify_v3_3c_check.md").read_text()


# ---------------------------------------------------------------------------
# Class registry
# ---------------------------------------------------------------------------

CLASS_NAMES: dict[str, str] = {
    "1A": "Canonical named glycan entity",
    "1B": "Named recurrent structural feature",
    "1C": "Non-GAG homo/hetero-polymer",         # NEW
    "2A": "Linkage-specified substructure",
    "2B": "Single descriptor phrase",
    "2C": "Composite descriptive phrase",
    "2D": "Glycoform shorthand code",
    "2E": "Composition formula",
    "3A": "Umbrella / glycoconjugate class",
    "3B": "Monosaccharide or named disaccharide",  # extended
    "3C": "Association-defined glycan marker",
    "X":  "Outside scheme",
}
TIER_OF: dict[str, str] = {k: k[0] if k != "X" else "X" for k in CLASS_NAMES}

VALID_CODES = set(CLASS_NAMES.keys())


# ---------------------------------------------------------------------------
# Stage 0 — Regex pre-classification
# ---------------------------------------------------------------------------

# Glycosidic linkage notation. Must be sugar-flavoured: anomeric letter (α/β)
# OR followed by 'linked'/'branch', AND the digits must be 1-2 chars (real
# linkages are α2-3, β1-4, 1-6 etc., never anything like '19-9').
_RE_LINKAGE = re.compile(
    r"""
    [αβ]\s*\d{1,2}\s*[-→]\s*\d{1,2}            # α2-6, β1→4 — anomeric letter required
    |                                             # OR
    \b[αβ]\d{1,2}                                 # α2, β1 (residue prefix style)
    |                                             # OR
    \b\d{1,2}\s*[-→]\s*\d{1,2}\s*-?\s*(?:linked|branch(?:ed)?|sialyl|fucos|fucosyl|gal)
                                                  # 1-4-linked, 1-6 branched, 2-3-sialylated
    """,
    re.IGNORECASE | re.VERBOSE,
)
_RE_COMPOSITION = re.compile(
    r"""^\s*
    (?:(?:Hex(?:NAc)?|NeuA?c?|NeuGc|Neu5Ac|Neu5Gc|Fuc|dHex|Pent|Xyl|Sulf|Phos|HexA)\s*\d+\s*){2,}
    \s*$""",
    re.VERBOSE,
)
_RE_COMPOSITION_SHORT = re.compile(r"^[HNFSPA]\d+(?:[HNFSPA]\d+)+$")

# Glycoform shorthand. IgG / Oxford / NGA / NA families. Robust to any combo.
# G0, G1, G2, G0F, G1F, G2F, G0FS1, G2FS2, FA2, FA2G2, FA2G2S2,
# M3, M5, M9, M7BC, M8B, A1, A2, A2[3], A2[3]G1, NGA2, NGA2F, NA2, NA4F.
_RE_GLYCOFORM_OXFORD = re.compile(
    r"""^\s*
    (?:                                          # leading family token
        (?:NGA|NA|FA|G|M|A)\d{1,2}              # G0, FA2, NGA2, M9, A2
    )
    (?:\[\d+\])?                                 # optional antenna bracket
    (?:                                          # optional further suffixes
        (?:                                       # repeated [letter[digit]] tokens
            (?:G|S|F|B|X|FX|BC|BG)\d*
        )
        |
        (?:                                       # bare suffix letters (FX, BC)
            [BFGSXFMA]
        )
    )*
    \s*$""",
    re.VERBOSE,
)

# Strict non-GAG polymer list. Membership match (case-insensitive).
_NON_GAG_POLYMERS = {
    "mannan",
    "α-glucan", "alpha-glucan", "a-glucan",
    "β-glucan", "beta-glucan", "b-glucan",
    "1,3-glucan", "1,4-glucan",
    "starch", "amylose", "amylopectin",
    "glycogen",
    "dextran",
    "cellulose",
    "pectin",
    "inulin", "levan",
    "agar", "agarose", "alginate", "alginic acid",
    "chitin", "chitosan",
    "arabinoxylan", "xylan", "glucuronoxylan",
    "apiogalacturonan", "arabinoglucuronoxylan",
    "fructan",
    "galactan", "β-galactan", "1-6 beta galactan",
    "1-3,1-4 beta glucan",
}

_GAG_NAMES = {
    "hyaluronan", "hyaluronic acid",
    "heparan sulfate", "heparin", "heparan sulphate",
    "keratan sulfate", "keratan sulphate",
    "chondroitin sulfate", "chondroitin sulphate",
    "chondroitin-4-sulfate", "chondroitin-6-sulfate",
    "chondroitin sulfate a", "chondroitin sulfate b", "chondroitin sulfate c",
    "dermatan sulfate", "dermatan sulphate",
    "chondroitin",
}


def regex_classify(term: str) -> tuple[str, str] | None:
    """Return (class_code, reason) when a deterministic match is found."""
    s = term.strip()
    low = s.lower()

    # 1C polymers — but never if it's a known GAG.
    if low in _NON_GAG_POLYMERS and low not in _GAG_NAMES:
        return "1C", "Listed non-GAG polymer."

    # 2A linkage notation — α/β + numeric, or N-N-linked patterns
    if _RE_LINKAGE.search(s):
        # But '1A canonical' modifiers like '6'-sulfo sialyl Lewis X' may also
        # contain '6'-' style digits. The numeric-dash-numeric (1-3, 1-4) is the
        # robust signal; do not fire on bare ordinal-prime patterns like '6-O-sulfo'.
        if re.search(r"\d+\s*[-→]\s*\d+", s):
            return "2A", "Explicit linkage notation present."

    # 2E composition formulas
    if _RE_COMPOSITION.match(s):
        return "2E", "Composition formula (Hex/HexNAc style)."
    if _RE_COMPOSITION_SHORT.match(s) and not re.match(r"^G\d+$", s):
        # exclude bare G3 / G4 which are ambiguous
        return "2E", "Composition formula (HNFS shorthand)."

    # 2D glycoform shorthand — Oxford / IgG / etc. Be conservative.
    # Common patterns: G0, G1F, G2FS1, FA2, FA2G2S2, M3, M9, A2, NGA2, NA2.
    if 2 <= len(s) <= 18 and _RE_GLYCOFORM_OXFORD.match(s) and re.search(r"\d", s):
        # G2 / G3 / G4 / G5 alone are ambiguous (globotriose family). Defer to LLM.
        if re.fullmatch(r"G[2345]", s):
            return None
        return "2D", "Glycoform shorthand code."

    return None


# ---------------------------------------------------------------------------
# JSON schemas (grammar-constrained)
# ---------------------------------------------------------------------------

SCHEMA_MAIN = {
    "type": "object",
    "additionalProperties": False,
    "required": ["class_code", "reason"],
    "properties": {
        "class_code": {"type": "string", "enum": sorted(VALID_CODES)},
        "reason": {"type": "string"},
    },
}

SCHEMA_2B_CHECK = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision", "reason"],
    "properties": {
        "decision": {
            "type": "string",
            "enum": [
                "KEEP_2B",
                "UPGRADE_1A", "UPGRADE_1B",
                "UPGRADE_2A", "UPGRADE_2C", "UPGRADE_2D", "UPGRADE_2E",
                "UPGRADE_3B",
            ],
        },
        "reason": {"type": "string"},
    },
}

SCHEMA_3C_CHECK = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision", "reason"],
    "properties": {
        "decision": {"type": "string", "enum": ["MAKE_3C", "KEEP_ORIGINAL"]},
        "reason": {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# LLM call helpers
# ---------------------------------------------------------------------------


def _build_chat_for_classification():
    """Low-reasoning, short num_predict, structured-output ChatOllama."""
    return build_chat_ollama(
        model_key="resolution_model",
        format=SCHEMA_MAIN,
        overrides={
            "reasoning": "low",
            "num_predict": 600,
            "temperature": 0.0,
            "top_p": 0.85,
            "seed": 2026,
        },
    )


def _build_chat_for_check(schema: dict):
    return build_chat_ollama(
        model_key="resolution_model",
        format=schema,
        overrides={
            "reasoning": "low",
            "num_predict": 200,
            "temperature": 0.0,
            "seed": 2026,
        },
    )


def llm_classify_main(model, term: str, hint_keywords: list[str]) -> dict:
    user = f"Term: {term!r}\n"
    if hint_keywords:
        user += f"Source-provided keywords: {', '.join(hint_keywords) or '(none)'}\n"
    user += (
        '\nReturn ONE JSON object: '
        '{"class_code": "...", "reason": "..."}'
    )
    resp = invoke_json(chat_model=model, system_prompt=SYS_PROMPT_MAIN, user_prompt=user)
    log_invocation_metadata(resp.invocation_metadata)
    return resp.payload


def llm_recheck_2b(model, term: str) -> dict:
    user = f"Term: {term!r}\n\nReturn ONE JSON object."
    resp = invoke_json(chat_model=model, system_prompt=SYS_PROMPT_2B, user_prompt=user)
    log_invocation_metadata(resp.invocation_metadata)
    return resp.payload


def llm_recheck_3c(model, term: str) -> dict:
    user = f"Term: {term!r}\n\nReturn ONE JSON object."
    resp = invoke_json(chat_model=model, system_prompt=SYS_PROMPT_3C, user_prompt=user)
    log_invocation_metadata(resp.invocation_metadata)
    return resp.payload


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_terms() -> list[dict]:
    nodes = json.loads(INPUT_NODES.read_text())
    out = []
    for n in nodes:
        lbl = (n.get("lbl") or "").strip()
        if not lbl:
            continue
        # Collect hint keywords from any source row's `keywords` metadata
        hint_kw: list[str] = []
        for src in (n.get("sources") or []):
            # Note: src_content isn't on the master_nodes pre-dedup version;
            # we just have src_lbl + src + src_uuid.
            pass
        # Some metadata bleeds through from postprocessing.update_master_registered_terms_file:
        # the node may have a `classification` / `keywords` already. Treat as hint.
        if isinstance(n.get("keywords"), list):
            hint_kw.extend(n["keywords"])
        # classification field now holds curator-assigned 3-tier code (if any)
        # after postprocessing_utils hoists suggested_class → classification.
        curator_class = (n.get("classification") or "").strip()
        out.append({
            "term_uuid": n["term_uuid"],
            "lbl": lbl,
            "gtc_id": n.get("gtc_id") or [],
            "source_classification": curator_class,
            "curator_class": curator_class,
            "hint_keywords": hint_kw,
            "n_sources": len(n.get("sources") or []),
        })
    return out


def load_already_classified() -> set[str]:
    if not OUT_TSV.exists():
        return set()
    done: set[str] = set()
    with OUT_TSV.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("term_uuid"):
                done.add(row["term_uuid"])
    return done


def append_tsv_row(path: Path, row: dict, fieldnames: list[str]) -> None:
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        if write_header:
            w.writeheader()
        w.writerow(row)


def append_audit(row: dict) -> None:
    with OUT_AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def classify_one(term_record: dict, models: dict, skip_stage_2: bool, no_llm: bool) -> tuple[dict, dict]:
    """Return (tsv_row, audit_row)."""
    lbl = term_record["lbl"]
    rec_audit: dict = {
        "term_uuid": term_record["term_uuid"],
        "lbl": lbl,
        "stage0": None,
        "stage1": None,
        "stage2_2b": None,
        "stage2_3c": None,
    }

    # ── Stage -1: Curator ground truth ───────────────────────────────
    # If the curator already assigned a valid 3-tier code, use it as-is.
    # This skips ALL downstream stages (regex, LLM).
    curator_class = (term_record.get("curator_class") or "").strip()
    if curator_class and curator_class in VALID_CODES:
        rec_audit["stage_curator"] = {"class_code": curator_class}
        tsv = {
            "term_uuid": term_record["term_uuid"],
            "lbl": lbl,
            "class_code": curator_class,
            "class_name": CLASS_NAMES[curator_class],
            "tier": TIER_OF[curator_class],
            "method": "curator",
            "reason": "Curator-assigned classification (ground truth)",
            "gtc_ids": "; ".join(term_record["gtc_id"]),
            "n_sources": term_record["n_sources"],
        }
        return tsv, rec_audit

    # ── Stage 0 ────────────────────────────────────────────────────────
    s0 = regex_classify(lbl)
    if s0:
        code, reason = s0
        rec_audit["stage0"] = {"class_code": code, "reason": reason}
        tsv = {
            "term_uuid": term_record["term_uuid"],
            "lbl": lbl,
            "class_code": code,
            "class_name": CLASS_NAMES[code],
            "tier": TIER_OF[code],
            "method": "regex",
            "reason": reason,
            "gtc_ids": "; ".join(term_record["gtc_id"]),
            "n_sources": term_record["n_sources"],
        }
        return tsv, rec_audit

    if no_llm:
        tsv = {
            "term_uuid": term_record["term_uuid"],
            "lbl": lbl,
            "class_code": "",
            "class_name": "",
            "tier": "",
            "method": "skipped",
            "reason": "LLM disabled",
            "gtc_ids": "; ".join(term_record["gtc_id"]),
            "n_sources": term_record["n_sources"],
        }
        return tsv, rec_audit

    # ── Stage 1: main classifier ──────────────────────────────────────
    final_code = ""
    final_reason = ""
    final_method = "llm"
    try:
        payload = llm_classify_main(models["main"], lbl, term_record["hint_keywords"])
        code = (payload.get("class_code") or "").strip()
        reason = (payload.get("reason") or "").strip()
        rec_audit["stage1"] = payload
        if code not in VALID_CODES:
            code = "X"
            reason = f"invalid class_code from LLM: {payload.get('class_code')!r}"
        final_code, final_reason = code, reason
    except (EmptyOllamaResponseError, Exception) as exc:
        rec_audit["stage1"] = {"error": str(exc)}
        final_code = "X"
        final_reason = f"LLM error: {exc}"

    # ── Stage 2a: 2B re-check ─────────────────────────────────────────
    if not skip_stage_2 and final_code == "2B":
        try:
            payload = llm_recheck_2b(models["check_2b"], lbl)
            rec_audit["stage2_2b"] = payload
            d = payload.get("decision", "")
            upgrade_map = {
                "UPGRADE_1A": "1A", "UPGRADE_1B": "1B",
                "UPGRADE_2A": "2A", "UPGRADE_2C": "2C",
                "UPGRADE_2D": "2D", "UPGRADE_2E": "2E",
                "UPGRADE_3B": "3B",
            }
            if d in upgrade_map:
                final_code = upgrade_map[d]
                final_reason = f"upgraded from 2B: {payload.get('reason','')}"
            # KEEP_2B: leave as-is
        except Exception as exc:
            rec_audit["stage2_2b"] = {"error": str(exc)}

    # ── Stage 2b: 3C recall check ─────────────────────────────────────
    if not skip_stage_2 and final_code in ("3A", "X"):
        try:
            payload = llm_recheck_3c(models["check_3c"], lbl)
            rec_audit["stage2_3c"] = payload
            if payload.get("decision") == "MAKE_3C":
                final_code = "3C"
                final_reason = f"3C recall upgrade: {payload.get('reason','')}"
        except Exception as exc:
            rec_audit["stage2_3c"] = {"error": str(exc)}

    tsv = {
        "term_uuid": term_record["term_uuid"],
        "lbl": lbl,
        "class_code": final_code,
        "class_name": CLASS_NAMES.get(final_code, "?"),
        "tier": TIER_OF.get(final_code, "?"),
        "method": final_method,
        "reason": final_reason,
        "gtc_ids": "; ".join(term_record["gtc_id"]),
        "n_sources": term_record["n_sources"],
    }
    return tsv, rec_audit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--skip-stage-2", action="store_true")
    p.add_argument("--force", action="store_true", help="re-classify even if already in output TSV")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    terms = load_terms()
    if args.start:
        terms = terms[args.start:]
    if args.limit:
        terms = terms[: args.limit]

    already = set() if args.force else load_already_classified()
    if already:
        print(f"[INIT] {len(already)} term(s) already classified, skipping.")
        terms = [t for t in terms if t["term_uuid"] not in already]

    print(f"[INIT] Classifying {len(terms)} term(s)…")
    print(f"[INIT] Output → {OUT_TSV}")
    print(f"[INIT] Audit  → {OUT_AUDIT}")

    fieldnames = ["term_uuid", "lbl", "class_code", "class_name", "tier",
                  "method", "reason", "gtc_ids", "n_sources"]

    if not args.no_llm:
        models = {
            "main": _build_chat_for_classification(),
            "check_2b": _build_chat_for_check(SCHEMA_2B_CHECK),
            "check_3c": _build_chat_for_check(SCHEMA_3C_CHECK),
        }
    else:
        models = {}

    counts: dict[str, int] = {}
    started = datetime.now()
    for i, t in enumerate(terms, start=1):
        tsv_row, audit_row = classify_one(t, models, args.skip_stage_2, args.no_llm)
        append_tsv_row(OUT_TSV, tsv_row, fieldnames)
        append_audit(audit_row)
        code = tsv_row["class_code"] or "(none)"
        counts[code] = counts.get(code, 0) + 1
        if i % 10 == 0 or i == len(terms):
            elapsed = (datetime.now() - started).total_seconds()
            print(f"[{i:>4d}/{len(terms)}]  {tsv_row['lbl'][:40]!r:42s} → {code}   "
                  f"(elapsed {elapsed:.0f}s, ~{(elapsed/i):.1f}s/term)")
    print("\n=== Class distribution ===")
    for k in sorted(counts):
        print(f"  {k:5s}  {counts[k]}")


if __name__ == "__main__":
    main()
