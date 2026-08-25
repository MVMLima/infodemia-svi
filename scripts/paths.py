"""Resolução do caminho do banco SQLite — SVI.

Ordem de precedência:
1. Variável de ambiente `SVI_DB_PATH` (recomendado para deploy/CI).
2. Campo `db_path` do `config.json` (opcional, p/ instalações customizadas).
3. Default: `<raiz do projeto>/data/infodemia.db`.

Uso:
    from paths import db_path
    DB_PATH = db_path()
"""
import json
import os
from pathlib import Path

DEFAULT_DB_NAME = "infodemia.db"


def projeto_root() -> Path:
    """Raiz do projeto (pasta que contém scripts/)."""
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return Path(__file__).resolve().parent / "config.json"


def db_path() -> str:
    """Retorna o caminho do banco SQLite conforme a precedência documentada."""
    env = os.environ.get("SVI_DB_PATH")
    if env:
        return env
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("db_path"):
            return cfg["db_path"]
    except Exception:
        pass
    return str(projeto_root() / "data" / DEFAULT_DB_NAME)
