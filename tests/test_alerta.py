"""Testes do alerta.py — watchdog silencioso."""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boatos  # noqa: E402
import alerta  # noqa: E402

SCHEMA = """
CREATE TABLE mencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, termo TEXT NOT NULL, titulo TEXT NOT NULL,
    url TEXT, fonte TEXT, sentimento TEXT, score INTEGER DEFAULT 0,
    boato_id INTEGER, exibida INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE boatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, descricao TEXT,
    taticas TEXT, keywords TEXT, narrativa_substituta TEXT NOT NULL,
    fontes_oficiais TEXT, status TEXT DEFAULT 'ativo'
);
CREATE TABLE picos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, termo TEXT NOT NULL, volume INTEGER NOT NULL,
    media_7d REAL, zscore REAL, acao TEXT,
    created_at TEXT DEFAULT (datetime('now')), UNIQUE(date, termo)
);
CREATE TABLE boatos_detectados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, boato_id INTEGER NOT NULL, termo TEXT,
    titulo TEXT, url TEXT, created_at TEXT DEFAULT (datetime('now'))
);
"""


class TestAlerta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.executescript(SCHEMA)
        boatos.seed_boatos(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_sem_alertas_silencioso(self):
        hoje = date.today().isoformat()
        texto = alerta.verificar_alertas(self.conn, hoje)
        self.assertEqual(texto, "")

    def test_pico_alerta_gera_texto(self):
        hoje = date.today().isoformat()
        self.conn.execute(
            """INSERT INTO picos (date, termo, volume, media_7d, zscore, acao)
               VALUES (?, 'vacina', 50, 5.0, 9.0, 'ALERTA')""",
            (hoje,),
        )
        self.conn.commit()
        texto = alerta.verificar_alertas(self.conn, hoje)
        self.assertIn("ALERTA INFODEMIA", texto)
        self.assertIn("vacina", texto)
        self.assertIn("9.00", texto)

    def test_boato_detectado_gera_texto(self):
        hoje = date.today().isoformat()
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM boatos WHERE slug='chip_vacina'")
        boato_id = cur.fetchone()[0]
        self.conn.execute(
            """INSERT INTO boatos_detectados (date, boato_id, termo, titulo, url)
               VALUES (?, ?, 'vacina', 'chip dentro da vacina', 'https://x.com')""",
            (hoje, boato_id),
        )
        self.conn.commit()
        texto = alerta.verificar_alertas(self.conn, hoje)
        self.assertIn("ALERTA INFODEMIA", texto)
        self.assertIn("Chip ou microchip na vacina", texto)

    def test_pico_observacao_nao_alerta(self):
        hoje = date.today().isoformat()
        self.conn.execute(
            """INSERT INTO picos (date, termo, volume, media_7d, zscore, acao)
               VALUES (?, 'vacina', 8, 7.0, 0.5, 'observacao')""",
            (hoje,),
        )
        self.conn.commit()
        texto = alerta.verificar_alertas(self.conn, hoje)
        self.assertEqual(texto, "")


if __name__ == "__main__":
    unittest.main()
