"""Testes do relatorio.py e marcar_exibidas.py — notícias + dedup."""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boatos  # noqa: E402
import relatorio  # noqa: E402
import marcar_exibidas  # noqa: E402

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


class TestRelatorioNoticias(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.executescript(SCHEMA)
        boatos.seed_boatos(self.conn)
        hoje = date.today().isoformat()
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento, exibida)
               VALUES (?, 'vacina', 'Nova vacina chega ao Acre', 'https://x.com/1', 'g1', 'positivo', 0)""",
            (hoje,),
        )
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento, exibida)
               VALUES (?, 'pandemia', 'Covid: boletim semanal', 'https://x.com/2', 'g1', 'neutro', 0)""",
            (hoje,),
        )
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento, exibida)
               VALUES (?, 'vacina', 'Notícia antiga já exibida', 'https://x.com/3', 'g1', 'neutro', 1)""",
            (hoje,),
        )
        self.conn.execute(
            """INSERT INTO picos (date, termo, volume, media_7d, zscore, acao)
               VALUES (?, 'pandemia', 15, 2.0, 6.5, 'ALERTA')""",
            (hoje,),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_relatorio_inclui_noticias_novas(self):
        hoje = date.today().isoformat()
        md = relatorio.gerar_relatorio(self.conn, hoje, dias=7)
        self.assertIn("## Notícias captadas", md)
        self.assertIn("Nova vacina chega ao Acre", md)
        self.assertIn("Covid: boletim semanal", md)
        self.assertNotIn("Notícia antiga já exibida", md)

    def test_relatorio_sem_noticias_novas(self):
        hoje = date.today().isoformat()
        marcar_exibidas.marcar_exibidas(self.conn, hoje, dias=7)
        md = relatorio.gerar_relatorio(self.conn, hoje, dias=7)
        self.assertIn("_Nenhuma notícia nova no período", md)
        self.assertNotIn("Nova vacina chega ao Acre", md)

    def test_marcar_exibidas_marca(self):
        hoje = date.today().isoformat()
        n = marcar_exibidas.marcar_exibidas(self.conn, hoje, dias=7)
        self.assertEqual(n, 2)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM mencoes WHERE exibida = 1")
        self.assertEqual(cur.fetchone()[0], 3)


class TestRelatorioV2(unittest.TestCase):
    """Testes das funções novas (ago/2026): resumo executivo, comparativo, veículo."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.executescript(SCHEMA)
        boatos.seed_boatos(self.conn)
        hoje = date.today()
        # Período atual (últimos 7d): vacina 2 menções; período anterior: vacina 1
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento)
               VALUES (?, 'vacina', 'Campanha de vacinação segue - G1', 'https://x.com/1', 'google_news', 'positivo')""",
            (hoje.isoformat(),),
        )
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento)
               VALUES (?, 'vacina', 'Nova dose disponível - A Gazeta do Acre', 'https://x.com/2', 'google_news', 'neutro')""",
            ((hoje - timedelta(days=1)).isoformat(),),
        )
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento, exibida)
               VALUES (?, 'chip vacina', 'Chip na vacina: mito ou verdade? - G1', 'https://x.com/3', 'google_news', 'negativo', 1)""",
            ((hoje - timedelta(days=3)).isoformat(),),
        )
        # Período ANTERIOR (hoje-13 a hoje-7): vacina 1 menção
        self.conn.execute(
            """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento)
               VALUES (?, 'vacina', 'Antiga matéria sobre vacinas - G1', 'https://x.com/4', 'google_news', 'neutro')""",
            ((hoje - timedelta(days=10)).isoformat(),),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_extrair_veiculo(self):
        self.assertEqual(relatorio.extrair_veiculo("Título qualquer - G1"), "G1")
        self.assertEqual(relatorio.extrair_veiculo("Sem separador de veículo"), "")
        self.assertEqual(relatorio.extrair_veiculo("Duplo - separador - O Juruá Em Tempo"), "O Juruá Em Tempo")

    def test_resumo_executivo_aparece_no_relatorio(self):
        hoje = date.today().isoformat()
        md = relatorio.gerar_relatorio(self.conn, hoje, dias=7)
        self.assertIn("## Resumo executivo", md)
        self.assertIn("**Negativas:**", md)
        self.assertIn("**Top termos (7d):**", md)

    def test_comparativo_calcula_delta(self):
        hoje = date.today()
        comp = relatorio._comparativo(self.conn, hoje, dias=7)
        por_termo = {t: (a, b, delta, var) for t, a, b, delta, var in comp}
        # vacina: 2 no atual, 1 no anterior (campanha antiga exibida cai fora? não — exibida=1 ainda conta)
        # Na verdade o comparativo conta TODAS as menções (exibidas ou não) por data.
        self.assertIn("vacina", por_termo)
        a, b, delta, var = por_termo["vacina"]
        self.assertEqual(a, 2)
        self.assertEqual(b, 1)
        self.assertEqual(delta, 1)

    def test_relatorio_inclui_veiculo(self):
        hoje = date.today().isoformat()
        md = relatorio.gerar_relatorio(self.conn, hoje, dias=7)
        self.assertIn("| G1 |", md)
        self.assertIn("A Gazeta do Acre", md)


if __name__ == "__main__":
    unittest.main()
