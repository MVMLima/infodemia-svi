"""Testes do boatos.py — normalização, seed e matching (anti-falso-positivo)."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boatos  # noqa: E402

SCHEMA_BOATOS = """
CREATE TABLE IF NOT EXISTS boatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, descricao TEXT,
    taticas TEXT, keywords TEXT, narrativa_substituta TEXT NOT NULL,
    fontes_oficiais TEXT, status TEXT DEFAULT 'ativo'
);
"""


class TestNormalizar(unittest.TestCase):
    def test_normalizar_basico(self):
        self.assertEqual(boatos.normalizar("Vacina É Perigosa"), "vacina e perigosa")

    def test_normalizar_acentos(self):
        self.assertEqual(boatos.normalizar("vacinação"), "vacinacao")
        self.assertEqual(boatos.normalizar("ÀS VEZES"), "as vezes")

    def test_normalizar_vazio(self):
        self.assertEqual(boatos.normalizar(""), "")
        self.assertEqual(boatos.normalizar(None), "")


class TestSeedBoatos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.execute(SCHEMA_BOATOS)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_seed_insere_10(self):
        n = boatos.seed_boatos(self.conn)
        self.assertEqual(n, 10)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM boatos")
        self.assertEqual(cur.fetchone()[0], 10)

    def test_seed_idempotente(self):
        boatos.seed_boatos(self.conn)
        n2 = boatos.seed_boatos(self.conn)
        self.assertEqual(n2, 0)

    def test_listar_boatos(self):
        boatos.seed_boatos(self.conn)
        lista = boatos.listar_boatos(self.conn)
        self.assertEqual(len(lista), 10)
        slugs = {b["slug"] for b in lista}
        self.assertIn("pandemia_fabricada", slugs)
        self.assertIn("chip_vacina", slugs)
        for b in lista:
            self.assertTrue(b["narrativa_substituta"])


class TestMatchBoato(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.execute(SCHEMA_BOATOS)
        boatos.seed_boatos(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_match_pandemia_fabricada(self):
        r = boatos.match_boato("a pandemia foi fabricada", self.conn)
        self.assertIsNotNone(r)
        self.assertEqual(r["slug"], "pandemia_fabricada")

    def test_match_chip(self):
        r = boatos.match_boato("vacina tem chip de rastreamento", self.conn)
        self.assertIsNotNone(r)
        self.assertEqual(r["slug"], "chip_vacina")

    def test_match_autismo_acentos(self):
        r = boatos.match_boato("vacina causa autismo em crianças", self.conn)
        self.assertIsNotNone(r)
        self.assertEqual(r["slug"], "vacina_autismo")

    def test_sem_match_inocuo(self):
        r = boatos.match_boato("campanha de vacinação avança no estado", self.conn)
        self.assertIsNone(r)

    def test_nao_casa_chip_sem_contexto_saude(self):
        r = boatos.match_boato("chip de segurança na nova carteira de identidade", self.conn)
        self.assertIsNone(r)

    def test_nao_casa_mata_sem_contexto_saude(self):
        r = boatos.match_boato("mata-mata da copa movimenta o fim de semana", self.conn)
        self.assertIsNone(r)

    def test_nao_casa_autismo_sem_contexto_saude(self):
        r = boatos.match_boato("autismo: novas terapias em estudo", self.conn)
        self.assertIsNone(r)

    def test_nao_casa_gravidez_sem_contexto_saude(self):
        r = boatos.match_boato("gravidez na adolescência preocupa secretaria", self.conn)
        self.assertIsNone(r)

    def test_nao_casa_resfriado_sem_contexto_saude(self):
        r = boatos.match_boato("estudo sobre resfriado comum em crianças", self.conn)
        self.assertIsNone(r)

    def test_casa_mata_com_contexto(self):
        r = boatos.match_boato("vacina mata idosos, diz estudo", self.conn)
        self.assertIsNotNone(r)
        self.assertEqual(r["slug"], "vacina_mata")

    def test_casa_gravidez_com_contexto(self):
        r = boatos.match_boato("vacina contra covid causa infertilidade e aborto", self.conn)
        self.assertIsNotNone(r)
        self.assertEqual(r["slug"], "vacina_infertilidade")

    def test_texto_vazio(self):
        self.assertIsNone(boatos.match_boato("", self.conn))
        self.assertIsNone(boatos.match_boato(None, self.conn))


if __name__ == "__main__":
    unittest.main()
