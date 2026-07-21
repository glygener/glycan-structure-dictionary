from __future__ import annotations

"""LangGraph workflow for entity resolution against the GSD vector store.

Processes query terms from source JSONL files through:
  retrieve -> resolve -> register -> advance (loop per term) -> END

Usage:
    python graph.py --source src_gsdv0 [--max-terms N] [--output-path PATH]
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

_PKG_DIR = Path(__file__).resolve().parent
SRC_ROOT = _PKG_DIR.parents[2]  # src/
for _p in (str(SRC_ROOT), str(_PKG_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from langchain_core.documents import Document
from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

# Import Chroma via the adapter so the sqlite3 shim runs before chromadb loads
# (and without any langchain_community fallback).
from gsd.adapters.chroma import Chroma

from gsd.adapters import (
    build_chat_model,
    build_embeddings,
    invoke_json,
    log_invocation_metadata,
)
from gsd.adapters.ollama import EmptyOllamaResponseError
from gsd.config import (
    load_chroma_config,
    load_models_config,
    load_ollama_config,
    load_paths_config,
)

from prompts import (
    RESOLUTION_SCHEMA,
    RESOLVER_SYSTEM_PROMPT,
    build_resolver_user_prompt,
)
from states import (
    QueryTerm,
    ResolveState,
    RetrievalCandidate,
)
from tools import query_textbook


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_NAME = "glycan_structure_dictionary"
TOP_K = 5
SCORE_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Chroma metadata helpers
# Chroma only accepts scalar metadata values (str, int, float, bool, None).
# Lists must be serialised to JSON strings before storage.
# ---------------------------------------------------------------------------


def _syns_to_meta(syns: list[str]) -> str:
    """Serialise a synonym list to a JSON string for Chroma metadata."""
    return json.dumps(syns, ensure_ascii=False)


def _meta_to_syns(val: str | list | None) -> list[str]:
    """Deserialise a Chroma metadata value back to a synonym list."""
    if val is None:
        return []
    if isinstance(val, list):          # shouldn't happen after fix, but be safe
        return val
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        # Fallback: treat as comma-separated string (legacy)
        return [s.strip() for s in val.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Graph context (injected via RunnableConfig)
# ---------------------------------------------------------------------------


@dataclass
class GraphContext:
    """Shared resources injected into every node via config["configurable"]["ctx"]."""

    vector_store: Any
    resolve_model: Any
    lookup_model: Any               # model with query_textbook bound as a tool
    resolve_model_fallback: Any     # format="json" fallback for MLX runner errors; None when not needed
    decisions_path: Path
    edges_path: Path


def _get_ctx(config: RunnableConfig) -> GraphContext:
    return config["configurable"]["ctx"]


# ---------------------------------------------------------------------------
# Node 1: Retrieve
# ---------------------------------------------------------------------------


def node_retrieve(state: ResolveState, config: RunnableConfig) -> dict[str, Any]:
    """Query the GSD vector store for candidate matches."""
    ctx = _get_ctx(config)
    idx = state.current_term_index

    if idx >= len(state.terms):
        return {"resolution_complete": True}

    term = state.terms[idx]
    query = term.surface_form
    if term.exact_synonyms or term.abbreviations:
        query += " " + " ".join(term.exact_synonyms + term.abbreviations)

    try:
        results = ctx.vector_store.similarity_search_with_relevance_scores(
            query=query,
            k=TOP_K,
            score_threshold=SCORE_THRESHOLD,
        )
    except Exception as exc:
        print(f"[NODE:retrieve] Vector search error for '{term.surface_form}': {exc}")
        return {"candidates": [], "errors": [f"retrieve: {exc}"]}

    candidates = []
    for doc, score in results:
        candidates.append(RetrievalCandidate(
            term=doc.metadata.get("term", ""),
            term_uuid=doc.metadata.get("term_uuid", ""),
            score=round(score, 4),
            exact_synonyms=_meta_to_syns(doc.metadata.get("exact_synonyms")),
            description=doc.metadata.get("description", ""),
        ))

    best = candidates[0].score if candidates else "N/A"
    print(f"[NODE:retrieve] '{term.surface_form}' -> {len(candidates)} candidates (best={best})")
    return {"candidates": candidates, "supplementary_info": ""}


# ---------------------------------------------------------------------------
# Node 2: Textbook Lookup (Essentials of Glycobiology RAG)
# ---------------------------------------------------------------------------

_TEXTBOOK_SYSTEM_PROMPT = (
    "You are a glycobiology expert. You have access to a query_textbook tool "
    "that retrieves passages from Essentials of Glycobiology (4th edition). "
    "Given a query glycan term and its candidate matches from our dictionary, "
    "decide whether textbook context would help disambiguate the relationship "
    "(e.g. is the query an abbreviation, a synonym, a more specific subtype, "
    "or a distinct structure?). "
    "If yes, call query_textbook ONCE with a precise free-text query that "
    "mentions the query glycan name plus what you want clarified (e.g. "
    "'sialyl Lewis x abbreviation synonym structure'). "
    "If the candidates already make the mapping decision obvious, do NOT call "
    "the tool. Never call it more than once."
)


def node_textbook_lookup(state: ResolveState, config: RunnableConfig) -> dict[str, Any]:
    """Optionally retrieve EoG textbook excerpts to supplement the resolver.

    The LLM synthesizes a textbook query and calls query_textbook if it judges
    that biology context would help disambiguate the current term against the
    candidates.
    """
    ctx = _get_ctx(config)
    idx = state.current_term_index
    term = state.terms[idx]
    candidates = state.candidates

    # No candidates → resolve will always be "add"; skip the LLM call entirely
    # to avoid long prompts that can crash the MLX runner.
    if not candidates:
        print(f"[NODE:textbook_lookup] '{term.surface_form}' -> skipped (no candidates, will auto-add)")
        return {"supplementary_info": ""}

    # Fast-path: weak top-1 → query term is almost certainly a new concept,
    # textbook context won't help the resolver. Saves ~5s on the long tail.
    top = candidates[0]
    runner_up_score = candidates[1].score if len(candidates) > 1 else 0.0
    if top.score < 0.55:
        print(
            f"[NODE:textbook_lookup] '{term.surface_form}' -> fast-path "
            f"(top={top.score} < 0.55, likely add)"
        )
        return {"supplementary_info": ""}

    # Fast-path: very confident top-1 → resolver will decide from the
    # candidate alone, textbook context is unnecessary.
    if top.score >= 0.7 and (top.score - runner_up_score) >= 0.05:
        print(
            f"[NODE:textbook_lookup] '{term.surface_form}' -> fast-path "
            f"(top={top.score} >= 0.7, margin>=0.05)"
        )
        return {"supplementary_info": ""}

    cand_lines = [
        f"- {c.term} (score={c.score}, uuid={c.term_uuid})"
        for c in candidates
    ]
    cand_summary = "\n".join(cand_lines)

    user_msg = (
        f'Query term: "{term.surface_form}"\n'
        f"Known synonyms: {', '.join(term.exact_synonyms) or '(none)'}\n\n"
        f"Retrieved candidates:\n{cand_summary}\n\n"
        "If the candidates are ambiguous or you need textbook biology to "
        "confirm the relationship, call query_textbook now with a single "
        "concise query. Otherwise do nothing."
    )

    try:
        ai_msg = ctx.lookup_model.invoke([
            {"role": "system", "content": _TEXTBOOK_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])

        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if not tool_calls:
            print(f"[NODE:textbook_lookup] '{term.surface_form}' -> skipped (LLM decided not needed)")
            return {"supplementary_info": ""}

        results: list[str] = []
        for tc in tool_calls[:1]:  # cap at one tool call to keep prompts compact
            tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            tool_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            if tool_name == "query_textbook":
                query = tool_args.get("query", term.surface_form)
                max_results = tool_args.get("max_results", 3)
                print(f"[NODE:textbook_lookup] '{term.surface_form}' -> textbook query: \"{query}\"")
                result = query_textbook.invoke({"query": query, "max_results": max_results})
                results.append(result)

        supplementary = "\n\n".join(results) if results else ""
        if supplementary:
            print(f"[NODE:textbook_lookup] Retrieved {len(results)} result block(s)")
        return {"supplementary_info": supplementary}

    except Exception as exc:
        print(f"[NODE:textbook_lookup] Error for '{term.surface_form}': {exc}")
        return {"supplementary_info": "", "errors": [f"textbook_lookup: {exc}"]}


# ---------------------------------------------------------------------------
# Node 3: Resolve (Entity Resolver Agent)
# ---------------------------------------------------------------------------


def node_resolve(state: ResolveState, config: RunnableConfig) -> dict[str, Any]:
    """LLM decides whether to map or add the current term."""
    ctx = _get_ctx(config)
    idx = state.current_term_index
    term = state.terms[idx]
    candidates = state.candidates

    # No candidates → always "add", no LLM needed.
    if not candidates:
        print(f"[NODE:resolve] '{term.surface_form}' -> add (no candidates, no LLM needed)")
        terms = list(state.terms)
        terms[idx] = term.model_copy(update={
            "action": "add",
            "mapped_to_uuid": "",
            "edge_type": "",
            "rationale": "No candidates found in vector store; registering as new term.",
            "resolved": True,
        })
        return {"terms": terms}

    # Fast-path: best candidate score is well below the meaningful-match
    # threshold AND the query has no GTC ID to cross-check. The resolver
    # would almost certainly say "add"; skip the LLM call to save ~6s.
    top_score = candidates[0].score
    if top_score < 0.45 and not (term.metadata.get("gtc_id") or []):
        print(f"[NODE:resolve] '{term.surface_form}' -> add (best score {top_score} < 0.45, no GTC)")
        terms = list(state.terms)
        terms[idx] = term.model_copy(update={
            "action": "add",
            "mapped_to_uuid": "",
            "edge_type": "",
            "rationale": f"All candidates below similarity threshold (best={top_score}); no GTC to cross-check.",
            "resolved": True,
        })
        return {"terms": terms}

    # Fast-path: GlyTouCan ID exact match. DISABLED for clean rebuild —
    # GSDv1's GTC IDs are unreliable and should not drive merge decisions.
    # The LLM will evaluate all candidates on semantic merit instead.
    ENABLE_GTC_FASTPATH = False
    query_gtcs = set(term.metadata.get("gtc_id", []) or [])
    if ENABLE_GTC_FASTPATH and query_gtcs:
        for c in candidates:
            try:
                got = ctx.vector_store.get(ids=[c.term_uuid])
                meta = got.get("metadatas", [{}])[0] if got and got.get("metadatas") else {}
                cand_gtc_str = meta.get("gtc_id", "")
                if isinstance(cand_gtc_str, str) and cand_gtc_str.startswith("["):
                    cand_gtcs_set = set(json.loads(cand_gtc_str))
                elif cand_gtc_str:
                    cand_gtcs_set = {cand_gtc_str}
                else:
                    cand_gtcs_set = set()
            except Exception:
                cand_gtcs_set = set()
            if query_gtcs & cand_gtcs_set:
                shared = sorted(query_gtcs & cand_gtcs_set)
                print(
                    f"[NODE:resolve] '{term.surface_form}' -> fast-path map "
                    f"(shared GTC {shared} with {c.term})"
                )
                terms = list(state.terms)
                terms[idx] = term.model_copy(update={
                    "action": "map",
                    "mapped_to_uuid": c.term_uuid,
                    "edge_type": "exact_synonym_of",
                    "rationale": f"Shared GlyTouCan ID {shared}.",
                    "resolved": True,
                })
                return {"terms": terms}

    # Fast-path: near-identical surface form after normalising whitespace /
    # case / punctuation. We require ANY moderate vector overlap (>=0.5) so
    # that random spurious string matches don't hijack the resolver.
    import re as _re
    def _normalise(s: str) -> str:
        # Case-sensitive carve-out: `i-antigen` (linear poly-LacNAc) and
        # `I-antigen` (branched poly-LacNAc) are different glycans. This
        # is the only term we treat as case-sensitive.
        if not s:
            return ""
        first_was_upper = s.lstrip()[:1] == "I"
        t = s.lower()
        # remove greek-letter variants and stylistic marks that vary between sources
        for src, dst in (("α", "a"), ("β", "b"), ("γ", "g"), ("δ", "d")):
            t = t.replace(src, dst)
        t = _re.sub(r"[\s\-_'`^()\[\]\.\,/]+", "", t)
        if t == "iantigen":
            t = "Iantigen_uc" if first_was_upper else "iantigen_lc"
        return t
    q_norm = _normalise(term.surface_form)
    # Check ALL retrieved candidates, not just top-3 — surface form match is
    # near-deterministic so the score floor is just a sanity gate.
    for c in candidates:
        if c.score < 0.5:
            continue
        cand_forms = [c.term] + list(c.exact_synonyms or [])
        if any(_normalise(f) == q_norm for f in cand_forms):
            print(
                f"[NODE:resolve] '{term.surface_form}' -> fast-path map "
                f"(surface-form match with {c.term}, score={c.score})"
            )
            terms = list(state.terms)
            terms[idx] = term.model_copy(update={
                "action": "map",
                "mapped_to_uuid": c.term_uuid,
                "edge_type": "exact_synonym_of",
                "rationale": f"Surface form matches candidate '{c.term}' after normalisation; vector score {c.score}.",
                "resolved": True,
            })
            return {"terms": terms}

    # Build candidates text for the prompt
    if candidates:
        lines = []
        for i, c in enumerate(candidates, 1):
            syns = ", ".join(c.exact_synonyms) if c.exact_synonyms else "(none)"
            lines.append(
                f"{i}. Term: {c.term}\n"
                f"   UUID: {c.term_uuid}\n"
                f"   Synonyms: {syns}\n"
                f"   Description: {c.description or '(none)'}\n"
                f"   Similarity: {c.score}"
            )
        candidates_text = "\n\n".join(lines)
    else:
        candidates_text = ""

    # Surface useful metadata from the source row (GTC IDs, IUPAC, etc.) so
    # the resolver can use them as evidence even when retrieval is weak.
    raw_extras_fields = []
    for k in ("gtc_id", "iupac_condensed", "db_xref", "classification"):
        v = term.metadata.get(k)
        if v:
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            raw_extras_fields.append(f"{k}={v}")
    raw_extras = " | ".join(raw_extras_fields) if raw_extras_fields else None

    user_prompt = build_resolver_user_prompt(
        query_term=term.surface_form,
        query_synonyms=term.exact_synonyms,
        query_description=term.description,
        candidates_text=candidates_text,
        supplementary_info=state.supplementary_info,
        curator_class=term.suggested_class,
        curator_notes=term.curator_notes,
        raw_extras=raw_extras,
    )

    try:
        response = invoke_json(
            chat_model=ctx.resolve_model,
            system_prompt=RESOLVER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        log_invocation_metadata(response.invocation_metadata)
        payload = response.payload
    except (EmptyOllamaResponseError, Exception) as exc:
        exc_str = str(exc)
        is_mlx_error = "mlx runner failed" in exc_str.lower()

        if is_mlx_error and ctx.resolve_model_fallback is not None:
            # The MLX runner crashed under grammar-constrained schema decoding.
            # Retry with format="json" (simple JSON mode), which MLX supports.
            print(
                f"[NODE:resolve] MLX runner error for '{term.surface_form}' — "
                f"retrying with format='json' fallback model..."
            )
            try:
                response = invoke_json(
                    chat_model=ctx.resolve_model_fallback,
                    system_prompt=RESOLVER_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
                log_invocation_metadata(response.invocation_metadata)
                payload = response.payload
            except Exception as fallback_exc:
                print(
                    f"[NODE:resolve] Fallback also failed for '{term.surface_form}': "
                    f"{fallback_exc}"
                )
                payload = {
                    "action": "add",
                    "mapped_to_uuid": "",
                    "edge_type": "",
                    "rationale": f"MLX error + fallback failed, defaulting to add: {fallback_exc}",
                }
        else:
            print(f"[NODE:resolve] LLM error for '{term.surface_form}': {exc}")
            payload = {
                "action": "add",
                "mapped_to_uuid": "",
                "edge_type": "",
                "rationale": f"LLM error, defaulting to add: {exc}",
            }

    action = payload.get("action", "add").lower().strip()
    mapped_to_uuid = payload.get("mapped_to_uuid", "").strip()
    edge_type = payload.get("edge_type", "").strip()
    rationale = payload.get("rationale", "").strip()

    # Validate the mapping UUID is from the retrieved candidates
    if action == "map":
        valid_uuids = {c.term_uuid for c in candidates}
        if mapped_to_uuid not in valid_uuids:
            print(
                f"[NODE:resolve] WARNING: mapped UUID '{mapped_to_uuid}' not in candidates "
                f"for '{term.surface_form}'. Falling back to add."
            )
            action = "add"
            mapped_to_uuid = ""
            edge_type = ""
            rationale += " [UUID not in candidates, fell back to add]"

    terms = list(state.terms)
    terms[idx] = term.model_copy(update={
        "action": action,
        "mapped_to_uuid": mapped_to_uuid,
        "edge_type": edge_type,
        "rationale": rationale,
        "resolved": True,
    })

    action_label = f"map -> {mapped_to_uuid[:16]}..." if action == "map" else "add (new)"
    print(f"[NODE:resolve] '{term.surface_form}' -> {action_label}")

    return {"terms": terms}


# ---------------------------------------------------------------------------
# Curator-hint helpers (used by node_register)
# ---------------------------------------------------------------------------


_CURATOR_STUB_XREF = "SRC:CURATOR_NOTES"


def _resolve_or_stub_target(ctx, target_label: str) -> str:
    """Return a term_uuid for `target_label`, creating a stub node if needed.

    Stub nodes get marked with metadata.placeholder=true so a later pass can
    merge them with a real entry that shares the surface form.
    """
    try:
        results = ctx.vector_store.similarity_search_with_relevance_scores(
            query=target_label, k=1, score_threshold=0.0,
        )
    except Exception:
        results = []
    if results:
        doc, score = results[0]
        if score >= 0.85:
            uid = doc.metadata.get("term_uuid")
            if uid:
                return uid

    # Stub
    new_uuid = f"GSD:{uuid4()}"
    page_content = (
        f"Term: {target_label}\n"
        f"Exact Synonyms: \n"
        f"Description: (stub created from curator notes; awaiting real entry)\n"
        f"Term UUID: {new_uuid}"
    )
    try:
        ctx.vector_store.add_documents(
            ids=[new_uuid],
            documents=[Document(
                page_content=page_content,
                metadata={
                    "term": target_label,
                    "term_uuid": new_uuid,
                    "exact_synonyms": _syns_to_meta([]),
                    "description": "(curator-notes stub)",
                    "gtc_id": json.dumps([], ensure_ascii=False),
                    "placeholder": True,
                },
                id=new_uuid,
            )],
        )
    except Exception as exc:
        print(f"[stub] Vector store add error for {target_label!r}: {exc}")
    return new_uuid


def _emit_curator_hint_edge(ctx, term: QueryTerm, hint) -> None:
    """Honor one curator hint. Updates terms.jsonl-equivalent edges_*.jsonl.

    `hint` is a CuratorHint model or a dict (the loader produces dicts/objects
    depending on which path created it).
    """
    pred = getattr(hint, "pred", None) or hint.get("pred")
    target_label = getattr(hint, "target_label", None) or hint.get("target_label")
    if not pred or not target_label:
        return

    # exact_synonym_of / abbreviation_of: append target_label to the query's
    # synonyms in the vector store (when mapped) and don't emit a real edge.
    if pred in ("exact_synonym_of", "abbreviation_of"):
        try:
            if term.mapped_to_uuid:
                got = ctx.vector_store.get(ids=[term.mapped_to_uuid])
                if got and got["documents"]:
                    meta = dict(got["metadatas"][0])
                    syns = _meta_to_syns(meta.get("exact_synonyms"))
                    if target_label not in syns:
                        syns.append(target_label)
                        meta["exact_synonyms"] = _syns_to_meta(syns)
                        new_doc = Document(
                            page_content=got["documents"][0],
                            metadata=meta,
                            id=term.mapped_to_uuid,
                        )
                        ctx.vector_store.update_document(
                            document_id=term.mapped_to_uuid, document=new_doc,
                        )
        except Exception as exc:
            print(f"[curator-hint] synonym append error: {exc}")
        return

    # Separate-node preds (related/broad/narrow synonym, is_a) — resolve or
    # stub the target, then emit an edge with the QUERY as subject. The
    # query's own GSD UUID is mapped_to_uuid (set above in node_register's
    # add branch, or carried over for map).
    subj_uuid = term.mapped_to_uuid
    if not subj_uuid:
        return
    obj_uuid = _resolve_or_stub_target(ctx, target_label)
    edge = {
        "subj": subj_uuid,
        "pred": pred,
        "obj": obj_uuid,
        "xref": term.xref,
        "comment": f"curator-hint: {term.surface_form} {pred} {target_label}",
    }
    with open(ctx.edges_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(edge, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Node 4: Register
# ---------------------------------------------------------------------------


def node_register(state: ResolveState, config: RunnableConfig) -> dict[str, Any]:
    """Register the decision: update vector store for 'add', write decision log."""
    ctx = _get_ctx(config)
    idx = state.current_term_index
    term = state.terms[idx]

    mapped_count_delta = 0
    added_count_delta = 0
    terms = list(state.terms)

    if term.action == "add":
        new_uuid = f"GSD:{uuid4()}"
        terms[idx] = term.model_copy(update={"mapped_to_uuid": new_uuid})
        term = terms[idx]

        syn_str = ", ".join(term.exact_synonyms) if term.exact_synonyms else ""
        page_content = (
            f"Term: {term.surface_form}\n"
            f"Exact Synonyms: {syn_str}\n"
            f"Description: {term.description}\n"
            f"Term UUID: {new_uuid}"
        )
        new_term_gtc = term.metadata.get("gtc_id", []) or []
        if isinstance(new_term_gtc, str):
            new_term_gtc = [new_term_gtc] if new_term_gtc else []
        doc = Document(
            page_content=page_content,
            metadata={
                "term": term.surface_form,
                "term_uuid": new_uuid,
                "exact_synonyms": _syns_to_meta(term.exact_synonyms),
                "description": term.description or "",
                "gtc_id": json.dumps(new_term_gtc, ensure_ascii=False),
            },
            id=new_uuid,
        )
        try:
            ctx.vector_store.add_documents(ids=[new_uuid], documents=[doc])
        except Exception as exc:
            print(f"[NODE:register] Vector store add error: {exc}")

        added_count_delta = 1

    elif term.action == "map":
        # Update vector store document with new synonym
        try:
            retrieved = ctx.vector_store.get(ids=[term.mapped_to_uuid])
            if retrieved and retrieved["documents"]:
                old_content = retrieved["documents"][0]
                old_meta = retrieved["metadatas"][0] if retrieved["metadatas"] else {}

                existing_syns = _meta_to_syns(old_meta.get("exact_synonyms"))
                if term.surface_form not in existing_syns:
                    updated_syns = existing_syns + [term.surface_form]
                else:
                    updated_syns = existing_syns

                syn_line = f"Exact Synonyms: {', '.join(updated_syns)}"
                lines = old_content.split("\n")
                updated_lines = [
                    syn_line if line.startswith("Exact Synonyms:") else line
                    for line in lines
                ]
                updated_meta = dict(old_meta)
                updated_meta["exact_synonyms"] = _syns_to_meta(updated_syns)

                updated_doc = Document(
                    page_content="\n".join(updated_lines),
                    metadata=updated_meta,
                    id=term.mapped_to_uuid,
                )
                ctx.vector_store.update_document(
                    document_id=term.mapped_to_uuid,
                    document=updated_doc,
                )
        except Exception as exc:
            print(f"[NODE:register] Vector store update error: {exc}")

        mapped_count_delta = 1

    # Write decision to JSONL log
    decision = {
        "source_term": term.surface_form,
        "src_uuid": term.src_uuid,
        "xref": term.xref,
        "mapped_to_uuid": term.mapped_to_uuid or "",
        "action": term.action,
        "edge_type": term.edge_type or "",
        "rationale": term.rationale,
    }
    with open(ctx.decisions_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(decision, ensure_ascii=False) + "\n")

    # Write edge for mapped terms
    if term.action == "map" and term.edge_type:
        edge = {
            "subj": term.src_uuid,
            "pred": term.edge_type,
            "obj": term.mapped_to_uuid,
            "xref": term.xref,
            "comment": f"{term.surface_form} {term.edge_type} {term.mapped_to_uuid}",
        }
        with open(ctx.edges_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    # Curator-hint edges. The curator declared `Has X Y.` style relations in
    # the notes column; we honour them HERE (after the LLM's own decision).
    # For each parsed hint:
    #   * Try to resolve the target_label against the vector store (cosine
    #     similarity >= 0.85 on the top-1 candidate).
    #   * If found, emit an edge (the query's own UUID → target's UUID).
    #   * If not found, create a stub node for the target with a fresh GSD
    #     UUID + a SRC:CURATOR_NOTES xref + metadata.placeholder=true, then
    #     emit the edge. Stub nodes may merge with real entries later when
    #     those entries are encountered organically.
    for hint in (term.curator_hints or []):
        try:
            _emit_curator_hint_edge(ctx, term, hint)
        except Exception as exc:
            print(f"[NODE:register] curator hint emit error for {hint}: {exc}")

    return {
        "terms": terms,
        "mapped_count": state.mapped_count + mapped_count_delta,
        "added_count": state.added_count + added_count_delta,
    }


# ---------------------------------------------------------------------------
# Node 5: Advance
# ---------------------------------------------------------------------------


def node_advance(state: ResolveState, config: RunnableConfig) -> dict[str, Any]:
    """Move to the next term."""
    remove_msgs = [
        RemoveMessage(id=m.id)
        for m in state.messages
        if hasattr(m, "id") and m.id
    ]

    next_idx = state.current_term_index + 1
    if next_idx >= len(state.terms):
        return {
            "resolution_complete": True,
            "messages": remove_msgs,
            "candidates": [],
        }

    return {
        "current_term_index": next_idx,
        "messages": remove_msgs,
        "candidates": [],
        "supplementary_info": "",
    }


# ---------------------------------------------------------------------------
# Routing conditions
# ---------------------------------------------------------------------------


def route_after_advance(state: ResolveState) -> str:
    return "end" if state.resolution_complete else "retrieve"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

graph = StateGraph(ResolveState)

graph.add_node("retrieve", node_retrieve)
graph.add_node("textbook_lookup", node_textbook_lookup)
graph.add_node("resolve", node_resolve)
graph.add_node("register", node_register)
graph.add_node("advance", node_advance)

graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "textbook_lookup")
graph.add_edge("textbook_lookup", "resolve")
graph.add_edge("resolve", "register")
graph.add_edge("register", "advance")
graph.add_conditional_edges("advance", route_after_advance, {
    "retrieve": "retrieve",
    "end": END,
})

app = graph.compile()


# ---------------------------------------------------------------------------
# Graph diagram
# ---------------------------------------------------------------------------


def save_graph_png(diagram_path: Path) -> None:
    """Save the compiled graph topology as a Mermaid PNG."""
    diagram_path.parent.mkdir(parents=True, exist_ok=True)
    with open(diagram_path, "wb") as f:
        f.write(app.get_graph().draw_mermaid_png())
    print(f"[GRAPH] Diagram saved: {diagram_path}")


# ---------------------------------------------------------------------------
# Load terms from source JSONL
# ---------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Curator-notes parser. The curator wrote `Has X Y.` -style relation hints
# in raw_terms_review.xlsx. Convert them into structured CuratorHints so the
# resolver / node_register can act on them.
# --------------------------------------------------------------------------

_NOTES_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("exact_synonym_of",   re.compile(r"has\s+exact\s+synonym\s+(.+?)(?:\.|$)", re.IGNORECASE)),
    ("abbreviation_of",    re.compile(r"(?:has\s+abbreviation|is\s+abbreviation\s+of)\s+(.+?)(?:\.|$)", re.IGNORECASE)),
    ("related_synonym_of", re.compile(r"has\s+(?:related\s+synonym|synonym)\s+(.+?)(?:\.|$)", re.IGNORECASE)),
    ("broad_synonym_of",   re.compile(r"has\s+broad\s+synonym\s+(.+?)(?:\.|$)", re.IGNORECASE)),
    ("narrow_synonym_of",  re.compile(r"has\s+narrow\s+synonym\s+(.+?)(?:\.|$)", re.IGNORECASE)),
    ("is_a",               re.compile(r"(?:is\s+a\s+kind\s+of|is_a)\s+(.+?)(?:\.|$)", re.IGNORECASE)),
]


def parse_curator_notes(notes: str | None) -> list:
    """Return list of {'pred', 'target_label'} dicts parsed from notes."""
    if not notes:
        return []
    hints: list[dict] = []
    for pred, rx in _NOTES_PATTERNS:
        for m in rx.finditer(notes):
            target = m.group(1).strip(' \'"`')
            if target:
                # Strip a trailing period that the regex may have included.
                target = target.rstrip(".").strip()
                if target:
                    hints.append({"pred": pred, "target_label": target})
    return hints


def load_source_terms(source_dir: Path) -> list[QueryTerm]:
    """Load terms from a source's terms.jsonl file.

    Rows with `keep == false` are dropped (per curator decision in xlsx).
    Curator hints from `metadata.bgsl_curator_meta` are threaded through.
    """
    terms_file = source_dir / "terms.jsonl"
    if not terms_file.exists():
        raise FileNotFoundError(f"No terms.jsonl in {source_dir}")

    terms = []
    n_dropped_keep = 0
    with open(terms_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)

            term_text = entry.get("term", "").strip()
            if not term_text or term_text == "[DISCARD]":
                continue

            if entry.get("keep") is False:
                n_dropped_keep += 1
                continue

            metadata = entry.get("metadata", {})
            curator_meta = metadata.get("bgsl_curator_meta") or {}
            # Also accept curator meta nested top-level in some early sources.
            if not curator_meta and entry.get("bgsl_curator_meta"):
                curator_meta = entry["bgsl_curator_meta"]

            # If the curator block says keep=false (legacy), respect it.
            if curator_meta.get("keep") is False:
                n_dropped_keep += 1
                continue

            curator_notes = curator_meta.get("notes")
            hints = parse_curator_notes(curator_notes)

            terms.append(QueryTerm(
                surface_form=term_text,
                src_uuid=entry.get("src_uuid", ""),
                xref=entry.get("xref", ""),
                exact_synonyms=metadata.get("exact_synonyms", []) or [],
                abbreviations=metadata.get("abbreviations", []) or [],
                description=metadata.get("description", "") or "",
                classification=metadata.get("classification", "") or "",
                metadata=metadata,
                suggested_class=curator_meta.get("suggested_class") or None,
                preferred_label_override=curator_meta.get("preferred_label_override") or None,
                curator_notes=curator_notes or None,
                curator_hints=hints,
            ))

    if n_dropped_keep:
        print(f"[LOAD] dropped {n_dropped_keep} row(s) with keep=false in {source_dir.name}")
    return terms


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def resolve_source_terms(
    source_id: str,
    output_path: Path | None = None,
    max_terms: int | None = None,
) -> Path:
    """Run the entity resolution workflow for a single source."""
    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()
    models_cfg = load_models_config()
    ollama_cfg = load_ollama_config()

    inputs_dir = Path(paths_cfg["data"]["inputs"])
    source_dir = inputs_dir / source_id

    if output_path is None:
        output_path = source_dir / "terms_resolved.jsonl"

    decisions_path = source_dir / "terms_ai-decisions.jsonl"
    edges_path = source_dir / "edges_ai-decisions.jsonl"

    # Load vector store (provider-agnostic embeddings)
    enrichment_cfg = chroma_cfg.get("enrichment", {})
    persist_dir = enrichment_cfg.get(
        "persist_directory",
        str(Path(paths_cfg["workspace"]["chroma"]) / "enrichment"),
    )

    embeddings = build_embeddings()
    provider = (models_cfg.get("provider") or "ollama").lower()

    vector_store = Chroma(
        persist_directory=str(persist_dir),
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )
    print(f"[INIT] Loaded vector store from {persist_dir} (provider={provider})")

    # Resolver LLM: schema-constrained JSON output.
    resolve_model = build_chat_model(
        model_key="resolution_model",
        format=RESOLUTION_SCHEMA,
    )

    # Fallback: same model, no format constraint. Used by node_resolve's
    # retry path. For OpenAI the fallback is just the same client.
    resolve_model_fallback: Any | None = (
        build_chat_model(model_key="resolution_model", format=None)
        if provider == "ollama"
        else None
    )

    # Lookup LLM: tool-calling enabled, no format constraint.
    lookup_model = build_chat_model(
        model_key="resolution_model",
        format=None,
    ).bind_tools([query_textbook])

    # Load terms
    terms = load_source_terms(source_dir)
    if max_terms is not None:
        terms = terms[:max_terms]
    print(f"[INIT] Loaded {len(terms)} terms from {source_id}")

    # Clear previous decision files
    for p in (decisions_path, edges_path):
        if p.exists():
            p.unlink()

    ctx = GraphContext(
        vector_store=vector_store,
        resolve_model=resolve_model,
        lookup_model=lookup_model,
        resolve_model_fallback=resolve_model_fallback,
        decisions_path=decisions_path,
        edges_path=edges_path,
    )
    runnable_config = {"configurable": {"ctx": ctx}}

    # Save graph diagram
    diagram_path = source_dir / "resolver_graph.png"
    try:
        save_graph_png(diagram_path)
    except Exception as exc:
        print(f"[GRAPH] Could not save diagram: {exc}")

    # Build initial state and run graph
    initial_state = ResolveState(
        source_id=source_id,
        terms=terms,
    )

    print(f"\n{'='*60}")
    print(f"Processing {len(terms)} terms from {source_id}")
    print(f"{'='*60}\n")

    try:
        final_state = app.invoke(initial_state, config=runnable_config)
    except Exception as exc:
        print(f"[ERROR] Graph execution failed: {exc}")
        raise

    # Write reconciled output: resolved term_uuids merged back into source format
    resolved_terms = final_state.get("terms", [])
    if resolved_terms and isinstance(resolved_terms[0], dict):
        resolved_terms = [QueryTerm(**t) for t in resolved_terms]

    with open(output_path, "w", encoding="utf-8") as fh:
        for term in resolved_terms:
            if not term.resolved:
                continue
            row = {
                "term": term.surface_form,
                "xref": term.xref,
                "term_uuid": term.mapped_to_uuid or "",
                "src_uuid": term.src_uuid,
                "metadata": term.metadata,
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    mapped = final_state.get("mapped_count", 0)
    added = final_state.get("added_count", 0)
    errors = final_state.get("errors", [])

    print(f"\n{'='*60}")
    print("Resolution Summary")
    print(f"{'='*60}")
    print(f"Source:               {source_id}")
    print(f"Total terms:          {len(terms)}")
    print(f"Mapped to existing:   {mapped}")
    print(f"Added as new:         {added}")
    print(f"Errors:               {len(errors)}")
    print(f"Decisions log:        {decisions_path}")
    print(f"Edges log:            {edges_path}")
    print(f"Resolved output:      {output_path}")

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve glycan structure terms against the GSD vector store."
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Source directory name (e.g. 'src_gsdv0', 'src_pubdictionaries').",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional output JSONL path for resolved terms.",
    )
    parser.add_argument(
        "--max-terms",
        type=int,
        default=None,
        help="Optional limit on terms to process (for testing).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    resolve_source_terms(
        source_id=args.source,
        output_path=args.output_path,
        max_terms=args.max_terms,
    )
