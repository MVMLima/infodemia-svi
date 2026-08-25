#!/usr/bin/env python3
"""
alerta.py — Alerta de infodemia (padrão watchdog para cron no_agent).

Se houver pico ALERTA ou boato detectado na data, imprime alerta em stdout.
Se nada houver, stdout VAZIO (silêncio = sem alerta) — ideal para cron no_agent.

Uso: python3 alerta.py [--date YYYY-MM-DD]
"""
import argparse
import sqlite3
from datetime import date
from pathlib import Path

from boatos import listar_boatos

from paths import db_path

DB_PATH = db_path()
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def verificar_alertas(conn: sqlite3.Connection, data_ref: str) -> str:
    """Retorna texto de alerta (ou string vazia se nada detectado)."""
    cursor = conn.cursor()

    # Picos com ALERTA na data
    cursor.execute(
        """SELECT termo, volume, media_7d, zscore FROM picos
           WHERE date = ? AND acao = 'ALERTA' ORDER BY zscore DESC""",
        (data_ref,),
    )
    picos = cursor.fetchall()

    # Boatos detectados na data
    cursor.execute(
        """SELECT bd.boato_id, bd.titulo, bd.url FROM boatos_detectados bd
           WHERE bd.date = ?""",
        (data_ref,),
    )
    boatos_det = cursor.fetchall()

    if not picos and not boatos_det:
        return ""

    boatos_by_id = {b["id"]: b for b in listar_boatos(conn)}
    partes: list[str] = []
    partes.append(f"🚨 ALERTA INFODEMIA — {data_ref}")

    if picos:
        partes.append("Picos de menção:")
        for termo, volume, media, zscore in picos:
            partes.append(f"  • {termo}: {volume} menções (média {media:.1f}, z {zscore:.2f})")

    if boatos_det:
        partes.append("Boatos circulando:")
        for boato_id, titulo, url in boatos_det:
            b = boatos_by_id.get(boato_id)
            nome = b["nome"] if b else f"boato#{boato_id}"
            partes.append(f"  • {nome} — {titulo[:100]}")
            if url:
                partes.append(f"    {url}")

    return "\n".join(partes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="Data de referência (YYYY-MM-DD)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    texto = verificar_alertas(conn, args.date)
    conn.close()

    if texto:
        print(texto)
    # stdout vazio = sem alerta (cron no_agent fica silencioso)


if __name__ == "__main__":
    main()
