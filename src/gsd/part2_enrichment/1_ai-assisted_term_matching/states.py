from __future__ import annotations

"""Pydantic state models for the entity-resolution LangGraph workflow.

The resolver processes one query term at a time through:
  retrieve -> resolve -> register -> advance -> (next term or END)
"""

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Candidate model (returned by vector search)
# ---------------------------------------------------------------------------


class RetrievalCandidate(BaseModel):
    """A candidate term returned by similarity search."""

    term: str
    term_uuid: str
    score: float
    exact_synonyms: list[str] = Field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Query term model (one per source-file row)
# ---------------------------------------------------------------------------


class CuratorHint(BaseModel):
    """A relation declared by the curator in the `notes` column.

    Example: a row whose notes contains `Has abbreviation Lex.` yields
    `CuratorHint(pred='abbreviation_of', target_label='Lex')`.
    """
    pred: str           # one of the edge_type values
    target_label: str   # the term the curator named; resolved to a node at register time


class QueryTerm(BaseModel):
    """A single query term to be resolved against the GSD vector store."""

    surface_form: str
    src_uuid: str
    xref: str
    exact_synonyms: list[str] = Field(default_factory=list)
    abbreviations: list[str] = Field(default_factory=list)
    description: str = ""
    classification: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Curator review-time hints (from data/inputs/raw_terms_review.xlsx,
    # threaded through normalize_new_sources via metadata.bgsl_curator_meta)
    suggested_class: str | None = None
    preferred_label_override: str | None = None
    curator_notes: str | None = None
    curator_hints: list[CuratorHint] = Field(default_factory=list)

    # Populated by the resolver
    action: str | None = None           # "map" | "add"
    mapped_to_uuid: str | None = None   # GSD UUID assigned or matched
    edge_type: str | None = None        # Relationship if mapped (exact_synonym_of, etc.)
    rationale: str = ""
    resolved: bool = False


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class ResolveState(BaseModel):
    """State for the entity-resolution graph.

    Processes a batch of query terms from a single source file.
    The graph loops over terms one at a time using current_term_index.
    """

    # --- Input (set before graph invocation) ---
    source_id: str                          # e.g. "src_gsdv0"
    terms: list[QueryTerm]                  # All terms from this source

    # --- Retrieval results for the current term ---
    candidates: list[RetrievalCandidate] = Field(default_factory=list)

    # --- Supplementary context (e.g. from PubMed) ---
    supplementary_info: str = ""

    # --- Messages for the resolver LLM ---
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # --- Routing signals ---
    current_term_index: int = 0
    resolution_complete: bool = False

    # --- Counters ---
    mapped_count: int = 0
    added_count: int = 0

    # --- Error tracking ---
    errors: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
