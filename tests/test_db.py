"""Testes do init_db.py — criação, idempotência e migração da coluna exibida."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Garante que scripts/ está no path
SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import init_db  # noqa: E402


class TestInitDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        init_db.DB_PATH = self.tmp.name

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_cria_tabelas(self):
        init_db.main()
        conn = sqlite3.connect(self.tmp.name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tabelas = [r[0] for r in cursor.fetchall()]
        for esperada in ["mencoes", "boatos", "picos", "boatos_detectados"]:
            self.assertIn(esperada, tabelas)
        conn.close()

    def test_idempotente(self):
        init_db.main()
        init_db.main()
        conn = sqlite3.connect(self.tmp.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='mencoes'")
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()

    def test_coluna_exibida_existe(self):
        init_db.main()
        conn = sqlite3.connect(self.tmp.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mencoes)")
        colunas = [r[1] for r in cursor.fetchall()]
        self.assertIn("exibida", colunas)
        conn.close()

    def test_migracao_banco_antigo(self):
        conn = sqlite3.connect(self.tmp.name)
        conn.execute(
            """CREATE TABLE mencoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL, termo TEXT NOT NULL, titulo TEXT NOT NULL,
                url TEXT, fonte TEXT, sentimento TEXT, score INTEGER DEFAULT 0,
                boato_id INTEGER, created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        conn.close()
        init_db.main()
        conn = sqlite3.connect(self.tmp.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mencoes)")
        colunas = [r[1] for r in cursor.fetchall()]
        self.assertIn("exibida", colunas)
        conn.close()


if __name__ == "__main__":
    unittest.main()
