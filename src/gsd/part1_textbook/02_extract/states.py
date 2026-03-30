from __future__ import annotations

"""Pydantic state models for the glycan term extraction LangGraph workflow."""

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Entity-level models
# ---------------------------------------------------------------------------


class Relation(BaseModel):
    """An abbreviation or structural-definition relation attached to a term."""

    relation_type: str  # "has_abbreviation" | "has_formula"
    target: str
    source_sentence_index: int


class ExtractedEntity(BaseModel):
    """A single extracted entity, progressively enriched through the graph."""

    surface_form: str
    first_sentence_index: int
    relations: list[Relation] = Field(default_factory=list)

    # Set by verify node
    verified: bool = False
    discarded: bool = False

    # Set by classify node
    classification: str | None = None
    classification_reason: str | None = None

    # Set by validate node
    validated: bool = False
    validation_attempts: int = 0


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class ChunkState(BaseModel):
    """State for processing one chunk pair through the extraction graph."""

    # Input context (set before graph invocation)
    chunk_id: str
    chapter: int
    tagged_text: str

    # Populated by extract node
    entities: list[ExtractedEntity] = Field(default_factory=list)

    # Reclassification feedback (classify ↔ validate loop)
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Routing signals
    current_entity_index: int = 0
    needs_reclassification: bool = False
    extraction_complete: bool = False

    # Error tracking
    errors: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
