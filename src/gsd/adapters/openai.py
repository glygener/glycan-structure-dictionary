"""OpenAI adapter — mirrors the Ollama adapter so the resolver pipeline can
switch providers via the `provider:` key in `configs/models.yaml` without
changing call sites.

Contract:
  - `build_chat_openai(model_key, overrides, format)` returns a `ChatOpenAI`
    instance bound to the configured model. `format` (a JSON-schema dict or
    `"json"`) is wired through `response_format`.
  - `build_openai_embeddings(model_name)` returns an `OpenAIEmbeddings`
    client.
  - `invoke_json(...)` mirrors `gsd.adapters.ollama.invoke_json` and returns
    an `OllamaJSONResponse`-shaped namedtuple-ish dataclass so call sites
    can be provider-agnostic.

Model-fallback ladder: when the configured model errors out with
"model not found", the adapter walks down a fallback list (gpt-5.4 →
gpt-5 → gpt-4o-mini) and remembers the working choice for subsequent calls.
The selected fallback is logged once per process.

Reasoning effort: when the resolved model name starts with `gpt-5`, `o1`,
`o3`, or `o4`, the adapter passes `reasoning_effort` through (default `low`
unless overridden). For other models the key is silently dropped.

`OPENAI_API_KEY` is loaded from the repo's `.env` file (via python-dotenv)
on import. If absent, the adapter raises at first use.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# Lazy dotenv load — finds gsd_v3/.env from anywhere in the package.
try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(_repo_root / ".env", override=False)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Shared response dataclasses (mirror gsd.adapters.ollama)
# ---------------------------------------------------------------------------


class EmptyOpenAIResponseError(ValueError):
    """Raised when a chat invocation returns no usable response content."""


@dataclass(slots=True)
class OpenAIInvocationMetadata:
    model: str | None
    finish_reason: str | None
    input_tokens: int | None
    reasoning_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(slots=True)
class OpenAIJSONResponse:
    payload: dict[str, Any]
    invocation_metadata: OpenAIInvocationMetadata
    text: str
    raw_message: Any


# ---------------------------------------------------------------------------
# Config + model-fallback ladder
# ---------------------------------------------------------------------------

_MODEL_LADDER = ["gpt-5.4", "gpt-5", "gpt-4o-mini"]

# Cache of resolved models per requested key, keyed by the originally
# requested name. After a model fails once, the working substitute is
# remembered so we don't re-walk the ladder on every call.
_RESOLVED: dict[str, str] = {}
_LOGGED_SUBS: set[str] = set()


def _resolve_model_with_fallback(requested: str) -> list[str]:
    """Return the ordered model list to try for this requested name."""
    already = _RESOLVED.get(requested)
    if already:
        return [already]
    candidates = [requested] + [m for m in _MODEL_LADDER if m != requested]
    return candidates


def _supports_reasoning(model_name: str) -> bool:
    return bool(re.match(r"^(gpt-5|o1|o3|o4)\b", model_name or ""))


# ---------------------------------------------------------------------------
# Public factories
# ---------------------------------------------------------------------------


def _load_model_cfg(model_key: str) -> dict[str, Any]:
    from gsd.config import load_models_config

    cfg = load_models_config()
    openai_cfg = cfg.get("openai") or {}
    block = openai_cfg.get(model_key)
    if not block:
        raise ValueError(
            f"models.yaml has no openai.{model_key} section. "
            f"Available keys: {sorted(openai_cfg.keys())}"
        )
    # Merge with shared defaults if any.
    merged: dict[str, Any] = dict(openai_cfg.get("default_params") or {})
    merged.update(block)
    return merged


def build_chat_openai(
    *,
    model_key: str,
    overrides: Mapping[str, Any] | None = None,
    format: str | dict[str, Any] | None = None,
) -> Any:
    """Return a ChatOpenAI bound to the resolved model.

    `format` semantics:
      - dict (JSON schema)  → response_format = {"type": "json_schema", ...}
      - "json"              → response_format = {"type": "json_object"}
      - None                → unstructured
    """
    try:
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "langchain-openai is required. Install it in the runtime env."
        ) from exc

    cfg = _load_model_cfg(model_key)
    if overrides:
        cfg = {**cfg, **overrides}

    requested = cfg.get("model") or "gpt-4o-mini"
    candidates = _resolve_model_with_fallback(requested)

    # Reasoning effort is per-model; the ChatOpenAI wrapper accepts it as
    # `reasoning_effort` for supporting models.
    cfg_reasoning = cfg.get("reasoning") or cfg.get("reasoning_effort")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not set. Add it to gsd_v3/.env or export it."
        )

    last_exc: Exception | None = None
    for model_name in candidates:
        try:
            kw: dict[str, Any] = {"model": model_name}
            # Sampling params (temperature/top_p) are decided per-candidate:
            # reasoning models (gpt-5*, o1/o3/o4) REJECT them — the API returns
            #   "Unsupported parameter: 'top_p' is not supported with this model"
            # (and likewise refuses a non-default temperature). Only forward
            # them to non-reasoning models (e.g. the gpt-4o-mini fallback).
            if not _supports_reasoning(model_name):
                if cfg.get("temperature") is not None:
                    kw["temperature"] = cfg["temperature"]
                if cfg.get("top_p") is not None:
                    kw["top_p"] = cfg["top_p"]
            if format is not None:
                if isinstance(format, dict):
                    # OpenAI's json_schema name must match ^[a-zA-Z0-9_-]+$.
                    raw_name = format.get("title") or model_key or "Response"
                    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_name).strip("_") or "Response"
                    kw["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": safe_name,
                            "schema": format,
                            "strict": True,
                        },
                    }
                elif format == "json":
                    kw["response_format"] = {"type": "json_object"}
            # When tools will be bound (format=None) reasoning_effort is not
            # supported on gpt-5.x for /v1/chat/completions. The caller signals
            # "tool-calling" by passing format=None — we skip reasoning then.
            if cfg_reasoning and _supports_reasoning(model_name) and format is not None:
                kw["reasoning_effort"] = cfg_reasoning
            client = ChatOpenAI(**kw)
            # Cache the working model for future calls with the same request.
            if model_name != requested:
                key = f"{requested}→{model_name}"
                if key not in _LOGGED_SUBS:
                    _LOGGED_SUBS.add(key)
                    print(
                        f"[openai-adapter] {requested!r} unavailable; "
                        f"falling back to {model_name!r}",
                        file=sys.stderr,
                    )
            _RESOLVED[requested] = model_name
            return client
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc or RuntimeError("no OpenAI model in the fallback ladder worked")


def build_openai_embeddings(model_name: str) -> Any:
    """Return an OpenAIEmbeddings client."""
    try:
        from langchain_openai import OpenAIEmbeddings
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "langchain-openai is required for OpenAI embeddings."
        ) from exc
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not set. Add it to gsd_v3/.env or export it."
        )
    return OpenAIEmbeddings(model=model_name)


# ---------------------------------------------------------------------------
# JSON-output helper
# ---------------------------------------------------------------------------


def invoke_json(
    *,
    chat_model: Any,
    system_prompt: str,
    user_prompt: str,
) -> OpenAIJSONResponse:
    """Call the chat model and parse a JSON response.

    Mirrors `gsd.adapters.ollama.invoke_json` so call sites are provider-
    agnostic.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    ai_msg = chat_model.invoke(messages)
    text = (getattr(ai_msg, "content", "") or "").strip()
    if not text:
        raise EmptyOpenAIResponseError("empty response from OpenAI chat")
    # Try strict JSON first; fall back to extracting a {...} block.
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise EmptyOpenAIResponseError(
                f"could not extract JSON from response: {text[:200]!r}"
            )
        payload = json.loads(m.group(0))

    usage = getattr(ai_msg, "usage_metadata", None) or {}
    meta = OpenAIInvocationMetadata(
        model=getattr(ai_msg, "response_metadata", {}).get("model_name"),
        finish_reason=getattr(ai_msg, "response_metadata", {}).get("finish_reason"),
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        reasoning_tokens=(usage.get("output_token_details") or {}).get("reasoning"),
        total_tokens=usage.get("total_tokens"),
    )
    return OpenAIJSONResponse(
        payload=payload,
        invocation_metadata=meta,
        text=text,
        raw_message=ai_msg,
    )


def log_invocation_metadata(meta: OpenAIInvocationMetadata) -> None:
    """Match the Ollama adapter's logging hook so call sites stay common."""
    parts = []
    if meta.model:
        parts.append(meta.model)
    if meta.input_tokens is not None:
        parts.append(f"in={meta.input_tokens}")
    if meta.reasoning_tokens:
        parts.append(f"think={meta.reasoning_tokens}")
    if meta.output_tokens is not None:
        parts.append(f"out={meta.output_tokens}")
    if meta.finish_reason:
        parts.append(f"done={meta.finish_reason}")
    if parts:
        print(f"[openai] {'  '.join(parts)}", file=sys.stderr)
