#!/usr/bin/env python3
"""Diagnóstico: distribuição de menções por data no banco SVI-AC."""
import sqlite3
from collections import Counter

from paths import db_path

conn = sqlite3.connect(db_path())
cur = conn.cursor()
cur.execute("SELECT date, COUNT(*) FROM mencoes GROUP BY date ORDER BY date DESC LIMIT 10")
for d, n in cur.fetchall():
    print(f"{d}: {n}")
print("---")
cur.execute("SELECT COUNT(*) FROM mencoes")
print(f"total mencoes: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM mencoes WHERE boato_id IS NOT NULL")
print(f"classificadas como boato: {cur.fetchone()[0]}")
conn.close()
