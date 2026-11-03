#!/usr/bin/env python3
"""
Coleta claims com veredito explicito de checadoras (ground truth externo).

Fonte: Google News RSS (mesmo mecanismo do coleta.py do SVI).
Padrao dos titulos das checadoras:
  "E #FAKE que <claim> - <veiculo>"        -> rotulo propagacao (claim falsa)
  "E verdade que <claim> - <veiculo>"      -> rotulo verdadeiro
  "<claim> e #FAKE - <veiculo>"            -> rotulo propagacao
"""
import csv
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CONSULTAS = [
    '"É #FAKE que" vacina',
    '"É #FAKE que" vacinação',
    '"É #FAKE que" covid',
    '"É #FAKE que" coronavírus',
    '"É #FAKE que" remédio saúde',
    '"É #FAKE que" cloroquina ivermectina',
    '"É #FAKE que" dengue',
    '"É verdade que" vacina',
    '"É verdade que" covid',
    '"É verdade que" dengue',
    '"Fato ou Fake:" vacina',
]

PREFIXO_FAKE = re.compile(
    r'^\s*["\u201c\u2018\'‘]?\s*[éeÉE]\s*#?\s*fake\s*(que|de que)?\s*[:,]?\s*',
    re.IGNORECASE)
PREFIXO_VERDADE = re.compile(
    r'^\s*["\u201c\u2018\'‘]?\s*[éeÉE]\s*verdade\s*(que|de que)?\s*[:,]?\s*',
    re.IGNORECASE)
SUFIXO_FONTE = re.compile(r'\s+-\s+[^-]{2,40}$')


def rss(q, when="1y"):
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(q) + f"&hl=pt-BR&gl=BR&ceid=BR:pt-419&when={when}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def limpar(t):
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    itens, vistos = [], set()
    for q in CONSULTAS:
        try:
            raiz = ET.fromstring(rss(q))
        except Exception as e:
            print(f"  [{q}] ERRO {e}")
            continue
        n = 0
        for it in raiz.iter("item"):
            titulo = limpar(it.findtext("title") or "")
            if not titulo:
                continue
            if PREFIXO_FAKE.match(titulo):
                rotulo, prov = "propagacao", "veredito_no_titulo"
                claim = PREFIXO_FAKE.sub("", titulo)
            elif PREFIXO_VERDADE.match(titulo):
                rotulo, prov = "verdadeiro", "veredito_no_titulo"
                claim = PREFIXO_VERDADE.sub("", titulo)
            else:
                continue
            claim = SUFIXO_FONTE.sub("", claim).strip(" -")
            if len(claim) < 25:
                continue
            chave = re.sub(r"[^a-z0-9]", "", claim.lower())[:80]
            if chave in vistos:
                continue
            vistos.add(chave)
            try:
                dt = parsedate_to_datetime(it.findtext("pubDate") or "").date().isoformat()
            except Exception:
                dt = ""
            itens.append(dict(data=dt, consulta=q, texto=claim,
                              rotulo=rotulo, fonte_rotulo=prov))
            n += 1
        print(f"  [{q}] +{n}")
        time.sleep(1.2)

    saida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "checagens.csv")
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["data", "consulta", "texto",
                                          "rotulo", "fonte_rotulo"])
        w.writeheader()
        w.writerows(itens)

    from collections import Counter
    print(f"\nGravado {saida}: {len(itens)} claims")
    for k, v in Counter(i["rotulo"] for i in itens).most_common():
        print(f"  {k}: {v}")
    for i in itens[:12]:
        print(f"  [{i['rotulo']:10s}] {i['texto'][:100]}")


if __name__ == "__main__":
    main()
