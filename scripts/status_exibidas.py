#!/usr/bin/env python3
"""Conta menções exibidas vs não-exibidas no banco SVI-AC."""
import sqlite3

from paths import db_path

conn = sqlite3.connect(db_path())
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM mencoes WHERE exibida = 0")
nao_exibidas = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM mencoes WHERE exibida = 1")
exibidas = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM mencoes")
total = cur.fetchone()[0]
conn.close()
print(f"total={total} | não exibidas={nao_exibidas} | exibidas={exibidas}")
