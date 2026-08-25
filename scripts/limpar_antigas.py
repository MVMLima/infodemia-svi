#!/usr/bin/env python3
"""Limpa menções com data fora da janela de 7 dias (lixo histórico do RSS)."""
import sqlite3
from datetime import date, timedelta

from paths import db_path

conn = sqlite3.connect(db_path())
limite = (date.today() - timedelta(days=7)).isoformat()
cur = conn.cursor()
cur.execute("DELETE FROM mencoes WHERE date < ?", (limite,))
n = cur.rowcount
conn.commit()
conn.close()
print(f"removidas {n} menções antigas (antes de {limite})")
