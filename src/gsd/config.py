import yaml
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_paths_config() -> dict[str, Any]:
    cfg = load_yaml(CONFIG_DIR / "paths.yaml")
    project_root_cfg = Path(cfg.get("project_root", "."))
    if project_root_cfg.is_absolute():
        project_root = project_root_cfg.resolve()
    else:
        project_root = (CONFIG_DIR.parent / project_root_cfg).resolve()

    def resolve_tree(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: resolve_tree(v) for k, v in obj.items()}
        if isinstance(obj, str):
            return (project_root / obj).resolve()
        return obj

    return resolve_tree(cfg)


def load_models_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "models.yaml")


def load_ollama_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "ollama.yaml")


def load_chroma_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "chroma.yaml")


def load_base_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "base.yaml")
