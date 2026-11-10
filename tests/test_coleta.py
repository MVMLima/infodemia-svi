"""Testes do coleta.py — parsing de RSS (com pubDate) e sentimento (sem rede)."""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import coleta  # noqa: E402


class TestResolucaoDeData(unittest.TestCase):
    """Item sem pubDate válido não pode ser datado pela coleta (pico fantasma de 02/08/2026)."""

    def test_pubdate_valida_usa_data_da_publicacao(self):
        data, fonte = coleta._resolver_data("Sat, 02 Aug 2026 10:30:00 GMT", "2026-08-09")
        self.assertEqual(data, "2026-08-02")
        self.assertEqual(fonte, "pubdate")

    def test_sem_pubdate_descarta_por_padrao(self):
        self.assertEqual(coleta._resolver_data("", "2026-08-09"), (None, None))
        self.assertEqual(coleta._resolver_data(None, "2026-08-09"), (None, None))

    def test_pubdate_invalida_descarta_por_padrao(self):
        self.assertEqual(coleta._resolver_data("data quebrada", "2026-08-09"), (None, None))

    def test_sem_pubdate_mantem_quando_configurado(self):
        data, fonte = coleta._resolver_data("", "2026-08-09", aceitar_sem_data=True)
        self.assertEqual(data, "2026-08-09")
        self.assertEqual(fonte, "fallback")


class TestParsingRSS(unittest.TestCase):
    def test_parse_news_xml_basico(self):
        xml = """<?xml version="1.0"?>
        <rss><channel>
        <item><title>Vacina contra covid chega ao Acre</title><link>https://g1.globo.com/ac</link><pubDate>Sat, 02 Aug 2026 10:30:00 GMT</pubDate></item>
        <item><title><![CDATA[Mais vacinas para o <b>estado</b>]]></title><link>https://exemplo.com/2</link><pubDate>Fri, 01 Aug 2026 08:00:00 GMT</pubDate></item>
        </channel></rss>"""
        itens = coleta.parse_news_xml(xml)
        self.assertEqual(len(itens), 2)
        self.assertEqual(itens[0]["titulo"], "Vacina contra covid chega ao Acre")
        self.assertEqual(itens[0]["url"], "https://g1.globo.com/ac")
        self.assertEqual(itens[1]["titulo"], "Mais vacinas para o estado")
        self.assertEqual(itens[0]["pubdate"], "Sat, 02 Aug 2026 10:30:00 GMT")

    def test_parse_news_xml_vazio(self):
        self.assertEqual(coleta.parse_news_xml("<rss></rss>"), [])

    def test_data_pubdate(self):
        self.assertEqual(
            coleta._data_pubdate("Sat, 02 Aug 2026 10:30:00 GMT"),
            "2026-08-02",
        )
        self.assertIsNone(coleta._data_pubdate(""))
        self.assertIsNone(coleta._data_pubdate("data inválida"))


class TestSentimento(unittest.TestCase):
    def test_positivo(self):
        r = coleta.analisar_sentimento("Vacina é segura, eficaz e protege a população")
        self.assertEqual(r["classificacao"], "positivo")

    def test_negativo(self):
        r = coleta.analisar_sentimento("Fraude na vacina, morte e pânico")
        self.assertEqual(r["classificacao"], "negativo")

    def test_vazio_neutro(self):
        r = coleta.analisar_sentimento("")
        self.assertEqual(r["classificacao"], "neutro")

    def test_sem_duplicacao_campanha(self):
        self.assertNotIn("campanha", coleta.POSITIVO)


if __name__ == "__main__":
    unittest.main()
