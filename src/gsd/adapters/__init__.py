"""Provider-agnostic factories for chat models + embeddings.

Reads the top-level `provider:` key in `configs/models.yaml` and routes to
either the Ollama or OpenAI adapter. Call sites only need:

    from gsd.adapters import build_chat_model, build_embeddings

and the rest of the code stays the same.

Fallback behaviour:
  - If `provider` is unset, defaults to `ollama` (the historical behaviour).
  - If a requested model key is missing from the active provider's config,
    raises a clear ValueError.
"""

from __future__ import annotations

from typing import Any, Mapping


def _active_provider() -> str:
    from gsd.config import load_models_config

    cfg = load_models_config()
    return (cfg.get("provider") or "ollama").lower()


def build_chat_model(
    *,
    model_key: str,
    overrides: Mapping[str, Any] | None = None,
    format: str | dict[str, Any] | None = "json",
) -> Any:
    """Return a chat-model instance for the active provider."""
    prov = _active_provider()
    if prov == "openai":
        from gsd.adapters.openai import build_chat_openai
        return build_chat_openai(model_key=model_key, overrides=overrides, format=format)
    if prov == "ollama":
        from gsd.adapters.ollama import build_chat_ollama
        return build_chat_ollama(model_key=model_key, overrides=overrides, format=format)
    raise ValueError(f"Unknown provider: {prov!r}")


def build_embeddings() -> Any:
    """Return an embedding-model instance for the active provider."""
    from gsd.config import load_models_config

    prov = _active_provider()
    cfg = load_models_config()
    if prov == "openai":
        from gsd.adapters.openai import build_openai_embeddings

        emb_cfg = (cfg.get("openai") or {}).get("embedding_model") or {}
        model = emb_cfg.get("model") or "text-embedding-3-small"
        return build_openai_embeddings(model)
    if prov == "ollama":
        from gsd.adapters.chroma import build_ollama_embeddings
        from gsd.config import load_ollama_config

        emb_cfg = (cfg.get("ollama") or {}).get("embedding_model") or {}
        model = emb_cfg.get("model") or "mxbai-embed-large:335m"
        host = load_ollama_config().get("host", "http://localhost:11434")
        return build_ollama_embeddings(model, host)
    raise ValueError(f"Unknown provider: {prov!r}")


def invoke_json(*, chat_model: Any, system_prompt: str, user_prompt: str):
    """Provider-agnostic invoke_json. Dispatches on class name."""
    cls = type(chat_model).__name__
    if cls.startswith("ChatOpenAI"):
        from gsd.adapters.openai import invoke_json as _ij
        return _ij(chat_model=chat_model, system_prompt=system_prompt, user_prompt=user_prompt)
    if cls.startswith("ChatOllama"):
        from gsd.adapters.ollama import invoke_json as _ij
        return _ij(chat_model=chat_model, system_prompt=system_prompt, user_prompt=user_prompt)
    # Generic fallback — try OpenAI first (newer codepath).
    from gsd.adapters.openai import invoke_json as _ij
    return _ij(chat_model=chat_model, system_prompt=system_prompt, user_prompt=user_prompt)


def log_invocation_metadata(meta: Any) -> None:
    cls = type(meta).__name__
    if "Ollama" in cls:
        from gsd.adapters.ollama import log_invocation_metadata as _lm
    else:
        from gsd.adapters.openai import log_invocation_metadata as _lm
    _lm(meta)
