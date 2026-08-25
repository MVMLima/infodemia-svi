#!/usr/bin/env python3
"""Reset flags exibida=0 para teste E2E do dedup (todas voltam a 'novas')."""
import sqlite3

from paths import db_path

conn = sqlite3.connect(db_path())
cur = conn.cursor()
cur.execute("UPDATE mencoes SET exibida = 0")
conn.commit()
n = cur.rowcount
conn.close()
print(f"reset: {n} menções marcadas como não-exibidas")
