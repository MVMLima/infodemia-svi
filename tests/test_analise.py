"""Testes do analise.py — detecção de picos e classificação de boatos."""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import analise  # noqa: E402

SCHEMA = """
CREATE TABLE mencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, termo TEXT NOT NULL, titulo TEXT NOT NULL,
    url TEXT, fonte TEXT, sentimento TEXT, score INTEGER DEFAULT 0,
    boato_id INTEGER, exibida INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_mencoes_uniq ON mencoes(date, termo, titulo);
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


class BaseAnaliseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            """INSERT INTO boatos (slug, nome, descricao, taticas, keywords, narrativa_substituta, fontes_oficiais, status)
               VALUES ('pandemia_fabricada', 'Pandemia fabricada', 'desc', '[]', '["fabricada"]', 'narrativa', '[]', 'ativo')"""
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)


class TestMediaMovel(BaseAnaliseTest):
    def test_media_movel_com_dias_zero(self):
        hoje = date.today()
        for i in range(1, 7):
            d = (hoje - timedelta(days=i)).isoformat()
            self.conn.execute(
                "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', ?)",
                (d, f"notícia dia {i}"),
            )
        hoje_str = hoje.isoformat()
        self.conn.execute("INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', 'pico de hoje')", (hoje_str,))
        self.conn.commit()

        media = analise.media_movel(self.conn, "vacina", hoje_str, janela=7)
        self.assertAlmostEqual(media, 6 / 7, places=5)

    def test_media_movel_sem_dados(self):
        hoje = date.today().isoformat()
        self.assertEqual(analise.media_movel(self.conn, "inexistente", hoje), 0.0)

    def test_serie_esparsa_nao_dispara_alerta(self):
        hoje = date.today()
        for i in (1, 2):
            d = (hoje - timedelta(days=i)).isoformat()
            self.conn.execute(
                "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', ?)",
                (d, f"esparso {i}"),
            )
        hoje_str = hoje.isoformat()
        for j in range(3):
            self.conn.execute(
                "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', ?)",
                (hoje_str, f"hoje {j}"),
            )
        self.conn.commit()

        picos = analise.detectar_picos(self.conn, hoje_str)
        self.assertEqual(len(picos), 0)


class TestDetectarPicos(BaseAnaliseTest):
    def test_pico_alerta(self):
        hoje = date.today()
        for i in range(1, 7):
            d = (hoje - timedelta(days=i)).isoformat()
            for j in range(2):
                self.conn.execute(
                    "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'pandemia', ?)",
                    (d, f"baseline {i}-{j}"),
                )
        hoje_str = hoje.isoformat()
        for j in range(20):
            self.conn.execute(
                "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'pandemia', ?)",
                (hoje_str, f"pico {j}"),
            )
        self.conn.commit()

        picos = analise.detectar_picos(self.conn, hoje_str)
        self.assertEqual(len(picos), 1)
        self.assertEqual(picos[0]["termo"], "pandemia")
        self.assertEqual(picos[0]["acao"], "ALERTA")
        self.assertGreaterEqual(picos[0]["zscore"], 2.0)

        cur = self.conn.cursor()
        cur.execute("SELECT acao FROM picos WHERE termo='pandemia' AND date=?", (hoje_str,))
        self.assertEqual(cur.fetchone()[0], "ALERTA")

    def test_sem_pico(self):
        hoje = date.today().isoformat()
        for i in range(3):
            self.conn.execute(
                "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', ?)",
                (hoje, f"normal {i}"),
            )
        self.conn.commit()
        picos = analise.detectar_picos(self.conn, hoje)
        self.assertEqual(len(picos), 0)


class TestClassificarMencoes(BaseAnaliseTest):
    def test_classifica_boato(self):
        hoje = date.today().isoformat()
        self.conn.execute(
            "INSERT INTO mencoes (date, termo, titulo, url) VALUES (?, 'pandemia', 'a pandemia foi fabricada', 'https://x.com/fab')",
            (hoje,),
        )
        self.conn.commit()

        n = analise.classificar_mencoes(self.conn, hoje)
        self.assertEqual(n, 1)

        cur = self.conn.cursor()
        cur.execute("SELECT boato_id FROM mencoes WHERE titulo='a pandemia foi fabricada'")
        self.assertIsNotNone(cur.fetchone()[0])

        cur.execute("SELECT termo, url FROM boatos_detectados WHERE titulo='a pandemia foi fabricada'")
        termo, url = cur.fetchone()
        self.assertEqual(termo, "pandemia")
        self.assertEqual(url, "https://x.com/fab")

        n2 = analise.classificar_mencoes(self.conn, hoje)
        self.assertEqual(n2, 0)
        cur.execute("SELECT COUNT(*) FROM boatos_detectados")
        self.assertEqual(cur.fetchone()[0], 1)

    def test_sem_boato(self):
        hoje = date.today().isoformat()
        self.conn.execute(
            "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'vacina', 'campanha de vacinação avança')",
            (hoje,),
        )
        self.conn.commit()
        n = analise.classificar_mencoes(self.conn, hoje)
        self.assertEqual(n, 0)

    def test_factcheck_nao_conta_como_propagacao(self):
        hoje = date.today().isoformat()
        self.conn.execute(
            "INSERT INTO mencoes (date, termo, titulo) VALUES (?, 'pandemia', 'É #FAKE que a pandemia foi fabricada, diz agência de checagem')",
            (hoje,),
        )
        self.conn.commit()
        n = analise.classificar_mencoes(self.conn, hoje)
        self.assertEqual(n, 0)
        cur = self.conn.cursor()
        cur.execute("SELECT boato_id FROM mencoes WHERE titulo LIKE '%FAKE%'")
        self.assertIsNotNone(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM boatos_detectados")
        self.assertEqual(cur.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
