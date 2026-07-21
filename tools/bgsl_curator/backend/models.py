"""Pydantic request models for the curator API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MergeReq(BaseModel):
    survivor: str
    absorbed: str
    relation: str = Field(description="exact_synonym | abbreviation")


class SplitChild(BaseModel):
    lbl: str
    src_uuids: list[str] = Field(default_factory=list)
    exact: list[str] = Field(default_factory=list)
    abbr: list[str] = Field(default_factory=list)
    gtc: list[str] | None = None
    classification: str | None = None


class SplitReq(BaseModel):
    parent: str
    children: list[SplitChild]
    edge_routing: dict[str, str] = Field(default_factory=dict)


class RelabelReq(BaseModel):
    new_lbl: str
    old_lbl_dest: str = "exact"  # exact | abbreviation | discard


class ListChange(BaseModel):
    action: str           # add | remove | move | rename
    field: str            # exact_synonyms | abbreviations
    value: str
    new_value: str | None = None


class ListEditReq(BaseModel):
    changes: list[ListChange]


class EdgeReq(BaseModel):
    action: str           # add | remove | modify
    subj: str
    pred: str
    obj: str
    comment: str | None = None
