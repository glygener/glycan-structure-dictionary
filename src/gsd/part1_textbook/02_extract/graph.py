from __future__ import annotations

"""LangGraph workflow for glycan term extraction, verification, classification, and validation.

Processes paired EOG textbook chunks through a multi-node graph:
  extract -> verify -> classify <-> validate -> advance (loop per entity) -> END

Usage:
    python src/gsd/part1_textbook/02_extract/graph.py [--output-path PATH] [--max-documents N]
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Path setup — 02_extract starts with a digit so standard dotted imports
# do not work.  Add both the src/ root and this package directory to sys.path.
_PKG_DIR = Path(__file__).resolve().parent
SRC_ROOT = _PKG_DIR.parents[2]  # src/
for _p in (str(SRC_ROOT), str(_PKG_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from gsd.adapters.ollama import (
    EmptyOllamaResponseError,
    build_chat_ollama,
    invoke_json,
    log_invocation_metadata,
)
from gsd.config import load_chroma_config, load_paths_config
from chunk_utils import (  # noqa: E402  (local package, digit-prefixed dir)
    build_extraction_user_prompt,
    extract_sentence_text,
    load_chunk_documents,
    load_sentence_uuid_map,
    pair_chunks,
    resolve_output_path,
)
from prompts import (  # noqa: E402
    CLASSIFICATION_SCHEMA,
    EXTRACTION_SCHEMA,
    VALIDATION_SCHEMA,
    VERIFICATION_SCHEMA,
    load_workflow_prompts,
)
from states import (  # noqa: E402
    ChunkState,
    ExtractedEntity,
    Relation,
)


# ---------------------------------------------------------------------------
# Graph context (injected via RunnableConfig)
# ---------------------------------------------------------------------------


@dataclass
class GraphContext:
    """Shared resources injected into every node via config["configurable"]["ctx"]."""

    extract_model: Any
    verify_model: Any
    classify_model: Any
    validate_model: Any
    extraction_prompt: str
    verification_prompt: str
    classification_system_prompt: str  # classification instructions + full scheme
    validation_prompt: str
    class_sections: dict[str, str]  # "1A" → isolated markdown section
    excluded_section: str
    allowed_classifications: set[str]
    max_validation_retries: int = 2


def _get_ctx(config: RunnableConfig) -> GraphContext:
    return config["configurable"]["ctx"]


# ---------------------------------------------------------------------------
# Node 1: Extract
# ---------------------------------------------------------------------------


def node_extract(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
    """Extract glycan terms and relations from the chunk (no classification)."""
    ctx = _get_ctx(config)

    user_prompt = build_extraction_user_prompt(
        state.chapter, state.chunk_id, state.tagged_text
    )

    try:
        response = invoke_json(
            chat_model=ctx.extract_model,
            system_prompt=ctx.extraction_prompt,
            user_prompt=user_prompt,
        )
        log_invocation_metadata(response.invocation_metadata)
    except (EmptyOllamaResponseError, Exception) as exc:
        print(f"[NODE:extract] LLM error: {exc}")
        return {"entities": [], "extraction_complete": True, "errors": [f"extract: {exc}"]}

    payload = response.payload
    raw_entities = payload.get("entities", [])
    if not isinstance(raw_entities, list):
        print("[NODE:extract] Invalid entities format, skipping chunk")
        return {"entities": [], "extraction_complete": True, "errors": ["extract: invalid entities format"]}

    # Deduplicate by surface_form, keeping lowest sentence index
    seen: dict[str, ExtractedEntity] = {}
    for item in raw_entities:
        if not isinstance(item, dict):
            continue
        sf = item.get("surface_form")
        raw_idx = item.get("first_sentence_index")
        if not isinstance(sf, str) or not sf.strip():
            continue
        if isinstance(raw_idx, str) and raw_idx.isdigit():
            raw_idx = int(raw_idx)
        if not isinstance(raw_idx, int) or raw_idx < 1:
            continue

        relations = []
        for rel in item.get("relations", []) or []:
            if not isinstance(rel, dict):
                continue
            rt = rel.get("relation_type", "")
            target = rel.get("target", "")
            src_idx = rel.get("source_sentence_index")
            if isinstance(src_idx, str) and src_idx.isdigit():
                src_idx = int(src_idx)
            if rt and target and isinstance(src_idx, int) and src_idx >= 1:
                relations.append(Relation(
                    relation_type=rt, target=target, source_sentence_index=src_idx
                ))

        if sf not in seen or raw_idx < seen[sf].first_sentence_index:
            seen[sf] = ExtractedEntity(
                surface_form=sf,
                first_sentence_index=raw_idx,
                relations=relations,
            )

    entities = sorted(seen.values(), key=lambda e: (e.first_sentence_index, e.surface_form))
    complete = len(entities) == 0
    print(f"[NODE:extract] {len(entities)} entities found")
    return {"entities": entities, "extraction_complete": complete}


# ---------------------------------------------------------------------------
# Node 2: Verify
# ---------------------------------------------------------------------------


def node_verify(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
    """Verify each entity's surface_form against its evidence sentence."""
    ctx = _get_ctx(config)
    entities = list(state.entities)
    new_entities: list[ExtractedEntity] = []
    errors: list[str] = []
    verified_count = 0
    split_count = 0
    discard_count = 0
    unverified_count = 0

    for i, entity in enumerate(entities):
        if entity.discarded:
            continue

        sentence = extract_sentence_text(state.tagged_text, entity.first_sentence_index)
        if sentence is None:
            # Cannot verify without sentence — keep unverified
            unverified_count += 1
            continue

        # Case-sensitive string match
        if entity.surface_form in sentence:
            entities[i] = entity.model_copy(update={"verified": True})
            verified_count += 1
            continue

        # LLM verification needed
        user_prompt = (
            f"Surface form: {entity.surface_form}\n"
            f"Sentence: {sentence}"
        )
        try:
            response = invoke_json(
                chat_model=ctx.verify_model,
                system_prompt=ctx.verification_prompt,
                user_prompt=user_prompt,
            )
            log_invocation_metadata(response.invocation_metadata)
        except (EmptyOllamaResponseError, Exception) as exc:
            # Keep unverified on LLM failure
            unverified_count += 1
            errors.append(f"verify: LLM error for '{entity.surface_form}': {exc}")
            continue

        payload = response.payload
        action = payload.get("action", "").lower().strip()

        if action == "accept":
            corrected = payload.get("surface_form", entity.surface_form)
            if isinstance(corrected, str) and corrected.strip():
                entities[i] = entity.model_copy(update={
                    "surface_form": corrected.strip(),
                    "verified": True,
                })
            else:
                entities[i] = entity.model_copy(update={"verified": True})
            verified_count += 1

        elif action == "split":
            # Mark original as discarded
            entities[i] = entity.model_copy(update={"discarded": True})
            dropped_relations = [r.model_dump() for r in entity.relations] if entity.relations else []
            if dropped_relations:
                errors.append(
                    f"verify: relations dropped on split of '{entity.surface_form}': {dropped_relations}"
                )

            # Create new entities from split
            for term in payload.get("terms", []) or []:
                if not isinstance(term, dict):
                    continue
                sf = term.get("surface_form")
                idx = term.get("first_sentence_index", entity.first_sentence_index)
                if isinstance(idx, str) and idx.isdigit():
                    idx = int(idx)
                if not isinstance(sf, str) or not sf.strip():
                    continue
                if not isinstance(idx, int) or idx < 1:
                    idx = entity.first_sentence_index

                new_relations = []
                for rel in term.get("relations", []) or []:
                    if not isinstance(rel, dict):
                        continue
                    rt = rel.get("relation_type", "")
                    target = rel.get("target", "")
                    src_idx = rel.get("source_sentence_index", idx)
                    if isinstance(src_idx, str) and src_idx.isdigit():
                        src_idx = int(src_idx)
                    if rt and target and isinstance(src_idx, int):
                        new_relations.append(Relation(
                            relation_type=rt, target=target, source_sentence_index=src_idx
                        ))

                new_entities.append(ExtractedEntity(
                    surface_form=sf.strip(),
                    first_sentence_index=idx,
                    relations=new_relations,
                    verified=True,
                ))
            split_count += 1

        elif action == "discard":
            entities[i] = entity.model_copy(update={"discarded": True})
            discard_count += 1

        else:
            # Unknown action — keep unverified
            unverified_count += 1
            errors.append(f"verify: unknown action '{action}' for '{entity.surface_form}'")

    # Append split-generated entities
    entities.extend(new_entities)

    # Set current_entity_index to first non-discarded entity
    first_active = _find_first_active(entities, 0)
    complete = first_active is None

    print(
        f"[NODE:verify] {verified_count} verified, {split_count} split, "
        f"{discard_count} discarded, {unverified_count} unverified"
    )

    return {
        "entities": entities,
        "current_entity_index": first_active or 0,
        "extraction_complete": complete,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Node 3: Classify
# ---------------------------------------------------------------------------


def node_classify(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
    """Classify the current entity."""
    ctx = _get_ctx(config)
    entities = list(state.entities)
    idx = state.current_entity_index

    if idx >= len(entities) or entities[idx].discarded:
        return {"extraction_complete": True}

    entity = entities[idx]
    sentence = extract_sentence_text(state.tagged_text, entity.first_sentence_index) or ""

    # Build user prompt
    user_prompt = f"Surface form: {entity.surface_form}\nSentence: {sentence}"

    # Append reclassification feedback if present
    if state.messages:
        last_msg = state.messages[-1]
        if hasattr(last_msg, "content") and last_msg.content:
            user_prompt += f"\n\nPrevious classification was rejected: {last_msg.content}"

    try:
        response = invoke_json(
            chat_model=ctx.classify_model,
            system_prompt=ctx.classification_system_prompt,
            user_prompt=user_prompt,
        )
        log_invocation_metadata(response.invocation_metadata)
    except (EmptyOllamaResponseError, Exception) as exc:
        print(f"[NODE:classify] LLM error for '{entity.surface_form}': {exc}")
        entities[idx] = entity.model_copy(update={"discarded": True})
        return {"entities": entities, "errors": [f"classify: {exc}"]}

    payload = response.payload
    classification = str(payload.get("classification", "")).strip().upper()
    reason = str(payload.get("reason", "")).strip()

    if classification == "DISCARD":
        entities[idx] = entity.model_copy(update={"discarded": True})
        print(f"[NODE:classify] entity='{entity.surface_form}' -> DISCARD")
        return {"entities": entities, "needs_reclassification": False}

    if classification not in ctx.allowed_classifications:
        print(f"[NODE:classify] invalid classification '{classification}' for '{entity.surface_form}', discarding")
        entities[idx] = entity.model_copy(update={"discarded": True})
        return {"entities": entities, "errors": [f"classify: invalid code '{classification}'"]}

    entities[idx] = entity.model_copy(update={
        "classification": classification,
        "classification_reason": reason,
    })
    print(f"[NODE:classify] entity='{entity.surface_form}' -> {classification}")
    return {"entities": entities, "needs_reclassification": False}


# ---------------------------------------------------------------------------
# Node 4: Validate
# ---------------------------------------------------------------------------


def node_validate(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
    """Validate the current entity's classification against isolated class criteria."""
    ctx = _get_ctx(config)
    entities = list(state.entities)
    idx = state.current_entity_index

    if idx >= len(entities) or entities[idx].discarded:
        return {"needs_reclassification": False}

    entity = entities[idx]
    entities[idx] = entity.model_copy(update={
        "validation_attempts": entity.validation_attempts + 1
    })
    entity = entities[idx]

    classification = entity.classification or ""
    class_section = ctx.class_sections.get(classification, "")
    excluded_section = ctx.class_sections.get("EXCLUDED", "")

    sentence = extract_sentence_text(state.tagged_text, entity.first_sentence_index) or ""

    user_prompt = (
        f"Surface form: {entity.surface_form}\n"
        f"Sentence: {sentence}\n"
        f"Assigned classification: {classification}\n\n"
        f"## Assigned class definition\n\n{class_section}\n\n"
        f"## Excluded tier\n\n{excluded_section}"
    )

    try:
        response = invoke_json(
            chat_model=ctx.validate_model,
            system_prompt=ctx.validation_prompt,
            user_prompt=user_prompt,
        )
        log_invocation_metadata(response.invocation_metadata)
    except (EmptyOllamaResponseError, Exception) as exc:
        # On validation failure, accept the classification as-is
        print(f"[NODE:validate] LLM error for '{entity.surface_form}': {exc}")
        entities[idx] = entity.model_copy(update={"validated": False})
        return {"entities": entities, "needs_reclassification": False, "errors": [f"validate: {exc}"]}

    payload = response.payload
    valid = payload.get("valid")
    reason = str(payload.get("reason", "")).strip()

    # Handle string "true"/"false" from LLM
    if isinstance(valid, str):
        valid = valid.lower().strip() == "true"

    if valid:
        entities[idx] = entity.model_copy(update={"validated": True})
        print(f"[NODE:validate] entity='{entity.surface_form}' class={classification} -> valid=True")
        return {"entities": entities, "needs_reclassification": False}

    # Invalid classification
    if entity.validation_attempts < ctx.max_validation_retries:
        print(
            f"[NODE:validate] Reclassifying '{entity.surface_form}' "
            f"(attempt {entity.validation_attempts}): {reason}"
        )
        # Add brief feedback message for the classify node
        feedback = HumanMessage(content=f"Class {classification} rejected: {reason}")
        return {
            "entities": entities,
            "needs_reclassification": True,
            "messages": [feedback],
        }

    # Max retries reached — keep last classification, mark unvalidated
    print(
        f"[NODE:validate] Max retries for '{entity.surface_form}' "
        f"class={classification}, keeping unvalidated"
    )
    entities[idx] = entity.model_copy(update={"validated": False})
    return {"entities": entities, "needs_reclassification": False}


# ---------------------------------------------------------------------------
# Node 5: Advance
# ---------------------------------------------------------------------------


def node_advance(state: ChunkState, config: RunnableConfig) -> dict[str, Any]:
    """Move to the next non-discarded entity, clearing reclassification messages."""
    # Clear messages from previous entity's reclassification loop
    remove_msgs = [RemoveMessage(id=m.id) for m in state.messages if hasattr(m, "id") and m.id]

    next_idx = _find_first_active(state.entities, state.current_entity_index + 1)
    if next_idx is None:
        return {
            "extraction_complete": True,
            "messages": remove_msgs,
            "needs_reclassification": False,
        }

    return {
        "current_entity_index": next_idx,
        "messages": remove_msgs,
        "needs_reclassification": False,
    }


# ---------------------------------------------------------------------------
# Routing conditions
# ---------------------------------------------------------------------------


def route_after_validate(state: ChunkState) -> str:
    """Route from validate: reclassify or advance."""
    if state.needs_reclassification:
        return "classify"
    return "advance"


def route_after_advance(state: ChunkState) -> str:
    """Route from advance: next entity or end."""
    if state.extraction_complete:
        return "end"
    return "classify"


def route_after_verify(state: ChunkState) -> str:
    """Route from verify: skip to end if no entities, else classify."""
    if state.extraction_complete:
        return "end"
    return "classify"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_first_active(entities: list[ExtractedEntity], start: int) -> int | None:
    """Find the index of the first non-discarded entity at or after start."""
    for i in range(start, len(entities)):
        if not entities[i].discarded:
            return i
    return None


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

graph = StateGraph(ChunkState)

graph.add_node("extract", node_extract)
graph.add_node("verify", node_verify)
graph.add_node("classify", node_classify)
graph.add_node("validate", node_validate)
graph.add_node("advance", node_advance)

graph.add_edge(START, "extract")
graph.add_edge("extract", "verify")
graph.add_conditional_edges("verify", route_after_verify, {
    "classify": "classify",
    "end": END,
})
graph.add_edge("classify", "validate")
graph.add_conditional_edges("validate", route_after_validate, {
    "classify": "classify",
    "advance": "advance",
})
graph.add_conditional_edges("advance", route_after_advance, {
    "classify": "classify",
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
# Main orchestration
# ---------------------------------------------------------------------------


def extract_eog_terms(
    output_path: Path | None = None,
    max_documents: int | None = None,
) -> Path:
    """Run the LangGraph extraction workflow over EOG chunk documents."""
    paths_cfg = load_paths_config()
    chroma_cfg = load_chroma_config()

    eog_chroma_cfg = chroma_cfg["eog"]
    persist_directory = Path(eog_chroma_cfg["persist_directory"]).resolve()
    collection_name = eog_chroma_cfg["collection_name"]

    # Load sentence UUID map
    sentence_map_path = (
        paths_cfg["resources"]["eog"]["indexed_sentences"] / "eog_sentence_map.jsonl"
    )
    sentence_uuid_map = load_sentence_uuid_map(sentence_map_path)

    # Load prompts and classification scheme
    prompts = load_workflow_prompts(paths_cfg)

    # Build classification system prompt (instructions + full scheme)
    classification_system_prompt = (
        f"{prompts.classification_prompt}\n\n"
        "## Reference classification scheme\n\n"
        f"{prompts.classification_scheme}"
    )

    # Build four ChatOllama instances (same model, different structured output schemas)
    extract_model = build_chat_ollama(model_key="extraction_model", format=EXTRACTION_SCHEMA)
    verify_model = build_chat_ollama(model_key="extraction_model", format=VERIFICATION_SCHEMA)
    classify_model = build_chat_ollama(model_key="extraction_model", format=CLASSIFICATION_SCHEMA)
    validate_model = build_chat_ollama(model_key="extraction_model", format=VALIDATION_SCHEMA)

    ctx = GraphContext(
        extract_model=extract_model,
        verify_model=verify_model,
        classify_model=classify_model,
        validate_model=validate_model,
        extraction_prompt=prompts.extraction_prompt,
        verification_prompt=prompts.verification_prompt,
        classification_system_prompt=classification_system_prompt,
        validation_prompt=prompts.validation_prompt,
        class_sections=prompts.class_sections,
        excluded_section=prompts.class_sections.get("EXCLUDED", ""),
        allowed_classifications=prompts.allowed_classifications,
    )

    runnable_config = {"configurable": {"ctx": ctx}}

    # Load and pair chunks
    chunk_documents = load_chunk_documents(persist_directory, collection_name)
    if max_documents is not None:
        chunk_documents = chunk_documents[:max_documents]
    invocation_documents = pair_chunks(chunk_documents)

    destination = resolve_output_path(paths_cfg, output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Save graph diagram
    diagram_path = destination.parent / "extraction_graph.png"
    try:
        save_graph_png(diagram_path)
    except Exception as exc:
        print(f"[GRAPH] Could not save diagram: {exc}")

    # Pipeline counters
    written = 0
    skipped_blank = 0
    skipped_no_map = 0
    skipped_dedup = 0
    skipped_discarded = 0
    skipped_unclassified = 0
    total_errors: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    total_chunks = len(invocation_documents)

    with destination.open("w", encoding="utf-8") as fh:
        for chunk_num, (chunk_id, chapter, merged_text) in enumerate(invocation_documents, 1):
            print(f"\n[CHUNK] Processing chunk {chunk_id} (chapter {chapter}) [{chunk_num}/{total_chunks}]")

            initial_state = ChunkState(
                chunk_id=chunk_id,
                chapter=chapter,
                tagged_text=merged_text,
            )

            # Run graph via invoke (returns final state dict)
            try:
                final_state = app.invoke(initial_state, config=runnable_config)
            except Exception as exc:
                print(f"[CHUNK] Graph execution error: {exc}")
                skipped_blank += 1
                total_errors.append(f"chunk {chunk_id}: {exc}")
                continue

            # Collect errors and entities from final state
            chunk_errors = final_state.get("errors", [])
            entities = final_state.get("entities", [])

            total_errors.extend(chunk_errors)

            # Write output rows
            for entity in entities:
                if isinstance(entity, dict):
                    entity = ExtractedEntity(**entity)

                if entity.discarded:
                    skipped_discarded += 1
                    continue
                if entity.classification is None:
                    skipped_unclassified += 1
                    continue

                src_uuid = sentence_uuid_map.get((chapter, entity.first_sentence_index))
                if src_uuid is None:
                    print(
                        f"[WARN] No sentence mapping for "
                        f"(chapter={chapter}, sentence={entity.first_sentence_index}) "
                        f"— surface_form={entity.surface_form!r} chunk={chunk_id}"
                    )
                    skipped_no_map += 1
                    continue

                pair = (entity.surface_form, src_uuid)
                if pair in seen_pairs:
                    skipped_dedup += 1
                    continue
                seen_pairs.add(pair)

                row = {
                    "surface_form": entity.surface_form,
                    "classification": entity.classification,
                    "classification_reason": entity.classification_reason or "",
                    "validated": entity.validated,
                    "src_uuid": src_uuid,
                    "relations": [r.model_dump() for r in entity.relations],
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1

            fh.flush()

    # Pipeline summary
    print("\n" + "=" * 60)
    print("Pipeline Summary")
    print("=" * 60)
    print(f"Source chunks:                       {len(chunk_documents)}")
    print(f"LLM invocation documents:            {total_chunks}")
    print(f"Wrote mentions:                      {written}")
    print(f"Skipped — discarded:                 {skipped_discarded}")
    print(f"Skipped — dedup (already written):   {skipped_dedup}")
    print(f"Skipped — no sentence map entry:     {skipped_no_map}")
    print(f"Skipped — unclassified:              {skipped_unclassified}")
    print(f"Skipped — graph errors:              {skipped_blank}")
    print(f"Total errors logged:                 {len(total_errors)}")
    print(f"Output JSONL: {destination}")

    return destination


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract glycan structural terms from EOG chunks using a LangGraph workflow."
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
        help="Optional limit on the number of Chroma chunk documents to process. set for testing with a smaller subset.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract_eog_terms(output_path=args.output_path, max_documents=args.max_documents)
