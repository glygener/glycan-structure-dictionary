from __future__ import annotations

"""Prompt loading and classification scheme section parsing.

Loads the four workflow prompts and the classification scheme from configs/,
and provides helpers for extracting per-class sections from the scheme for
token-efficient validation prompts.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# JSON schemas for structured output (ChatOllama format= parameter)
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "surface_form": {"type": "string"},
                    "first_sentence_index": {"type": "integer", "minimum": 1},
                    "relations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "relation_type": {"type": "string"},
                                "target": {"type": "string"},
                                "source_sentence_index": {"type": "integer", "minimum": 1},
                            },
                            "required": ["relation_type", "target", "source_sentence_index"],
                        },
                    },
                },
                "required": ["surface_form", "first_sentence_index"],
            },
        },
    },
    "required": ["entities"],
}

VERIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["accept", "split", "discard"]},
        "surface_form": {"type": "string"},
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "surface_form": {"type": "string"},
                    "first_sentence_index": {"type": "integer", "minimum": 1},
                    "relations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "relation_type": {"type": "string"},
                                "target": {"type": "string"},
                                "source_sentence_index": {"type": "integer", "minimum": 1},
                            },
                            "required": ["relation_type", "target", "source_sentence_index"],
                        },
                    },
                },
                "required": ["surface_form", "first_sentence_index"],
            },
        },
    },
    "required": ["action"],
}

CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classification": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["classification", "reason"],
}

VALIDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["valid", "reason"],
}


# ---------------------------------------------------------------------------
# Classification scheme section parser
# ---------------------------------------------------------------------------

# Matches headers like "### Class 1A. Canonical named glycan entity"
_CLASS_HEADER_RE = re.compile(r"^###\s+Class\s+(\w+)\.", re.MULTILINE)

# Matches the excluded tier header
_EXCLUDED_HEADER_RE = re.compile(r"^##\s+Excluded Tier", re.MULTILINE)


def parse_class_sections(scheme_text: str) -> dict[str, str]:
    """Parse the classification scheme markdown into per-class sections.

    Returns a dict mapping class code (e.g., "1A") to the markdown text
    for that class (from its ### header through to the next ### or ## header).
    Also returns an "EXCLUDED" key for the excluded tier section.
    """
    sections: dict[str, str] = {}

    # Find all class headers and the excluded header
    class_matches = list(_CLASS_HEADER_RE.finditer(scheme_text))
    excluded_match = _EXCLUDED_HEADER_RE.search(scheme_text)

    for i, match in enumerate(class_matches):
        code = match.group(1).upper()
        start = match.start()

        # End is next class header, excluded header, or end of text
        if i + 1 < len(class_matches):
            end = class_matches[i + 1].start()
        elif excluded_match and excluded_match.start() > start:
            end = excluded_match.start()
        else:
            end = len(scheme_text)

        sections[code] = scheme_text[start:end].strip()

    # Extract excluded tier
    if excluded_match:
        sections["EXCLUDED"] = scheme_text[excluded_match.start():].strip()

    return sections


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


@dataclass
class WorkflowPrompts:
    """All prompts and scheme data needed by the extraction workflow."""

    extraction_prompt: str
    verification_prompt: str
    classification_prompt: str
    classification_scheme: str
    validation_prompt: str
    class_sections: dict[str, str] = field(default_factory=dict)
    allowed_classifications: set[str] = field(default_factory=set)


def load_workflow_prompts(paths_cfg: dict[str, Any]) -> WorkflowPrompts:
    """Load all workflow prompts and parse the classification scheme.

    Reads prompt markdown files from paths configured in paths.yaml.
    """
    prompt_paths = paths_cfg["prompts"]

    extraction_prompt = Path(prompt_paths["glycan_term_extraction_only"]).read_text(
        encoding="utf-8"
    ).strip()

    verification_prompt = Path(prompt_paths["glycan_surface_form_verification"]).read_text(
        encoding="utf-8"
    ).strip()

    classification_prompt = Path(prompt_paths["glycan_term_classification_only"]).read_text(
        encoding="utf-8"
    ).strip()

    validation_prompt = Path(prompt_paths["glycan_classification_validation"]).read_text(
        encoding="utf-8"
    ).strip()

    classification_scheme = Path(prompt_paths["glycan_classification_scheme"]).read_text(
        encoding="utf-8"
    ).strip()

    class_sections = parse_class_sections(classification_scheme)
    allowed_classifications = {
        code for code in class_sections if code != "EXCLUDED"
    }

    return WorkflowPrompts(
        extraction_prompt=extraction_prompt,
        verification_prompt=verification_prompt,
        classification_prompt=classification_prompt,
        classification_scheme=classification_scheme,
        validation_prompt=validation_prompt,
        class_sections=class_sections,
        allowed_classifications=allowed_classifications,
    )
