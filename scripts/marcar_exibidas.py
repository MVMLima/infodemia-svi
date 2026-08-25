#!/usr/bin/env python3
"""
marcar_exibidas.py — marca notícias do período como já exibidas em briefing.

Uso: python3 marcar_exibidas.py [--date YYYY-MM-DD] [--dias N]
Rodar DEPOIS de gerar/entregar um briefing: impede que as mesmas notícias
apareçam no próximo relatório (campo exibida=1).

Retorna quantas notícias foram marcadas.
"""
import argparse
import sqlite3
from datetime import date, timedelta

from paths import db_path

DB_PATH = db_path()


def marcar_exibidas(conn: sqlite3.Connection, data_ref: str, dias: int = 7) -> int:
    """Marca como exibidas as menções (exibida=0) do período [data_ref-dias+1, data_ref]."""
    data_fim = date.fromisoformat(data_ref)
    data_ini = data_fim - timedelta(days=dias - 1)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE mencoes SET exibida = 1
           WHERE date BETWEEN ? AND ? AND exibida = 0""",
        (data_ini.isoformat(), data_fim.isoformat()),
    )
    conn.commit()
    return cursor.rowcount


def main() -> None:
    import json
    from pathlib import Path
    try:
        cfg = json.load(open(Path(__file__).parent / "config.json", encoding="utf-8"))
        dias_default = int(cfg.get("janela_dias", 7))
    except Exception:
        dias_default = 7
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="Data final do período (YYYY-MM-DD)")
    parser.add_argument("--dias", type=int, default=dias_default, help="Nº de dias do período (default do config.json)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    n = marcar_exibidas(conn, args.date, args.dias)
    conn.close()
    print(f"[marcar_exibidas] {n} notícia(s) marcada(s) como exibidas")


if __name__ == "__main__":
    main()
