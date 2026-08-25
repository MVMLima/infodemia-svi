#!/usr/bin/env python3
"""Distribuição de menções não-exibidas por data (banco SVI-AC)."""
import sqlite3
from datetime import date, timedelta

from paths import db_path

conn = sqlite3.connect(db_path())
cur = conn.cursor()
cur.execute("SELECT date, COUNT(*) FROM mencoes WHERE exibida=0 GROUP BY date ORDER BY date DESC")
print("não-exibidas por data:")
for d, n in cur.fetchall():
    print(f"  {d}: {n}")

# Janela de 7 dias
hoje = date.today()
ini = (hoje - timedelta(days=6)).isoformat()
cur.execute("SELECT COUNT(*) FROM mencoes WHERE exibida=0 AND date BETWEEN ? AND ?", (ini, hoje.isoformat()))
print(f"\nna janela 7d ({ini}..{hoje}): {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM mencoes WHERE exibida=0 AND date < ?", (ini,))
print(f"fora da janela (antes de {ini}): {cur.fetchone()[0]}")
conn.close()
