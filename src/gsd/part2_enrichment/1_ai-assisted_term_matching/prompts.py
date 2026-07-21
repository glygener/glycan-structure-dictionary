from __future__ import annotations

"""Prompts and JSON schemas for the entity-resolution LangGraph workflow.

The prompt text lives in configs/prompts/gsd_entity_resolution.md and the
JSON schema lives in configs/schemas/gsd_entity_resolution.schema.json.
This module loads them at import time via load_paths_config().
"""

import json
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
SRC_ROOT = _PKG_DIR.parents[2]  # src/
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gsd.config import load_paths_config


def _load_configs() -> tuple[str, dict]:
    """Load system prompt and JSON schema from config files."""
    paths_cfg = load_paths_config()

    prompt_path = paths_cfg["prompts"]["gsd_entity_resolution"]
    schema_path = paths_cfg["schemas"]["gsd_entity_resolution"]

    system_prompt = Path(prompt_path).read_text(encoding="utf-8").strip()

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    return system_prompt, schema


RESOLVER_SYSTEM_PROMPT, RESOLUTION_SCHEMA = _load_configs()


# ---------------------------------------------------------------------------
# User prompt builder
# ---------------------------------------------------------------------------


def build_resolver_user_prompt(
    query_term: str,
    query_synonyms: list[str],
    query_description: str,
    candidates_text: str,
    supplementary_info: str = "",
    *,
    curator_class: str | None = None,
    curator_notes: str | None = None,
    raw_extras: str | None = None,
) -> str:
    """Build the user prompt for the resolver LLM.

    Optional curator hints (from raw_terms_review.xlsx) are surfaced in a
    dedicated block; the resolver is instructed to respect them as ground
    truth. `raw_extras` carries source-side metadata like GlyTouCan IDs and
    IUPAC strings.
    """
    parts = [f'Query term: "{query_term}"']

    if query_synonyms:
        parts.append(f"Known synonyms: {', '.join(query_synonyms)}")
    if query_description:
        parts.append(f"Description: {query_description}")
    if raw_extras:
        parts.append(f"Source metadata: {raw_extras}")

    if curator_class or curator_notes:
        parts.append("")
        parts.append("## Curator hints (treat as ground truth)")
        if curator_class:
            parts.append(f"Class: {curator_class}")
        if curator_notes:
            parts.append(f"Notes: {curator_notes}")

    parts.append("")
    parts.append("## Potential matches in GSD vector store")
    parts.append(candidates_text if candidates_text.strip() else "(no candidates found)")

    if supplementary_info:
        parts.append("")
        parts.append("## Supplementary information")
        parts.append(supplementary_info)

    parts.append("")
    parts.append(
        "Analyze the query term against the potential matches above and decide "
        "whether to map it to an existing term or add it as a new entry."
    )
    # Explicit JSON-only instruction: required because the MLX runner path does
    # not enforce response format server-side — we rely on prompt compliance.
    parts.append("")
    parts.append(
        'Respond with ONLY a single JSON object matching this exact schema, '
        'and nothing else (no markdown, no commentary, no code fence):\n'
        '{\n'
        '  "action": "map" | "add",\n'
        '  "mapped_to_uuid": "<UUID of matched candidate if map, else \\"\\">",\n'
        '  "edge_type": "exact_synonym_of" | "related_synonym_of" | '
        '"abbreviation_of" | "broad_synonym_of" | "narrow_synonym_of" | '
        '"is_a" | "",\n'
        '  "rationale": "<brief reasoning>"\n'
        '}'
    )

    return "\n".join(parts)
