#!/usr/bin/env python3
"""Reset das tabelas de análise (boatos_detectados, picos, boato_id) para re-teste."""
import sqlite3

from paths import db_path

DB = db_path()

conn = sqlite3.connect(DB)
conn.execute("DELETE FROM boatos_detectados")
conn.execute("UPDATE mencoes SET boato_id = NULL")
conn.execute("DELETE FROM picos")
conn.commit()
print("reset ok")
conn.close()
