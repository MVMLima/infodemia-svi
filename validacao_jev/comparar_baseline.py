#!/usr/bin/env python3
"""Compara Jev x heuristica SO na populacao de producao (manchetes reais do SVI)
e categoriza os falsos negativos remanescentes."""
import csv
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "scripts"))

itens = {r["id"]: r for r in csv.DictReader(
    open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8"))}
res = [r for r in csv.DictReader(
    open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))]
for r in res:
    r["y"] = int(r["y"]); r["p_desinfo"] = float(r["p_desinfo"])
    r["texto"] = itens[r["id"]]["texto"]

norm = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                         if not unicodedata.combining(c))
from boatos import match_boato
import analise
SINAIS = [norm(s) for s in getattr(analise, "SINAIS_CHECAGEM", [])]
conn = sqlite3.connect(os.environ.get("SVI_DB_PATH",
                     "/home/marc/.hermes/data/infodemia/infodemia.db"))


def heuristica(t):
    if any(s in norm(t) for s in SINAIS):
        return 0
    return 1 if match_boato(t, conn) else 0


svi = [r for r in res if r["origem"] == "svi_ac"]
print(f"=== POPULACAO DE PRODUCAO: {len(svi)} manchetes reais do SVI (todas legit) ===")
h_fp = [r for r in svi if heuristica(r["texto"]) == 1]
j_fp = [r for r in svi if r["p_desinfo"] >= 0.5]
print(f"\nHeuristica SVI sinalizou como desinformacao: {len(h_fp)}/{len(svi)} "
      f"({100*len(h_fp)/len(svi):.1f}%)")
for r in h_fp:
    m = match_boato(r["texto"], conn)
    print(f"   -> boato='{m['slug'] if m else '?'}' | {r['texto'][:88]}")
print(f"\nJev sinalizou (corte 0.5): {len(j_fp)}/{len(svi)} ({100*len(j_fp)/len(svi):.1f}%)")
for r in j_fp:
    print(f"   -> p={r['p_desinfo']:.2f} | {r['texto'][:88]}")

# --- categorizacao dos falsos negativos (bateria limpa) ---
print("\n\n=== NATUREZA DOS FALSOS NEGATIVOS (p<0.5, y=1) ===")
MIDIA = re.compile(r"\b(foto|v[ií]deo|imagem|[aá]udio|print|cartaz|panfleto|postagem)\b", re.I)
NAO_SAUDE = re.compile(r"ceasa|desabastecimento|anatel|aposentadoria|cortella|falabella|"
                       r"tralli|hebraica|cuba|miguel|cortella|cesar|doria|onu|"
                       r"golpe usa|anúncio|anuncio", re.I)
cats = Counter()
exemplos = {}
for r in res:
    if r["y"] != 1 or r["p_desinfo"] >= 0.5:
        continue
    t = r["texto"]
    if MIDIA.search(t):
        c = "checagem de midia/autenticidade"
    elif NAO_SAUDE.search(t):
        c = "fora do escopo saude/narrativa"
    else:
        c = "erro genuino do modelo"
    cats[c] += 1
    exemplos.setdefault(c, []).append(t)
for c, n in cats.most_common():
    print(f"\n  {c}: {n}")
    for t in exemplos[c][:5]:
        print(f"     - {t[:90]}")

total_fn = sum(cats.values())
print(f"\n  total de falsos negativos: {total_fn}")
if cats.get("erro genuino do modelo"):
    print(f"  recalculando com apenas os erros genuinos: "
          f"revocacao = {(187 - cats['erro genuino do modelo'])/187:.3f}")
