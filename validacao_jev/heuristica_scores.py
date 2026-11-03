#!/usr/bin/env python3
"""Metricas da heuristica na MESMA bateria limpa usada para o Jev."""
import csv
import os
import re
import sqlite3
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "scripts"))

itens = {r["id"]: r for r in csv.DictReader(
    open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8"))}
res = [r for r in csv.DictReader(
    open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))]
MIDIA = re.compile(r"\b(foto|fotos|v[ií]deo|v[ií]deos|imagem|imagens|[aá]udio|print|prints|"
                   r"cartaz|panfleto|postagem|publica[çc][ãa]o|mensagem)\b", re.I)
MVERBO = re.compile(r"\b(mostr\w*|veicul\w*|seja|gravad\w*|filmad\w*|exib\w*|circul\w*)\b", re.I)
def midia(t): return bool(MIDIA.search(t) and MVERBO.search(t))

norm = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                         if not unicodedata.combining(c))
from boatos import match_boato
import analise
SINAIS = [norm(s) for s in getattr(analise, "SINAIS_CHECAGEM", [])]
conn = sqlite3.connect(os.environ.get("SVI_DB_PATH",
                     "/home/marc/.hermes/data/infodemia/infodemia.db"))

def heur(t):
    if any(s in norm(t) for s in SINAIS):
        return 0
    return 1 if match_boato(t, conn) else 0

def auc(ys, ps):
    p = sorted(zip(ps, ys)); n1 = sum(ys); n0 = len(ys) - n1
    if not n1 or not n0: return float("nan")
    rank, i, s = 1, 0, 0.0
    while i < len(p):
        j = i
        while j + 1 < len(p) and p[j+1][0] == p[i][0]: j += 1
        mr = (rank + rank + (j - i)) / 2
        s += sum(mr for k in range(i, j+1) if p[k][1] == 1)
        rank += (j - i + 1); i = j + 1
    return (s - n1*(n1+1)/2) / (n1*n0)

for nome, sub in (("bateria bruta (412)", res),
                  ("bateria limpa (378)", [r for r in res
                      if not (int(r["y"]) == 1 and midia(itens[r["id"]]["texto"]))])):
    ys = [int(r["y"]) for r in sub]
    ps = [heur(itens[r["id"]]["texto"]) for r in sub]
    tp = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 0)
    tn = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 0)
    prec = tp/(tp+fp) if tp+fp else float("nan")
    rec = tp/(tp+fn) if tp+fn else float("nan")
    f1 = 2*prec*rec/(prec+rec) if prec == prec and rec == rec and prec+rec else float("nan")
    brier = sum((p-y)**2 for y, p in zip(ys, ps))/len(ys)
    print(f"{nome}: n={len(ys)} acc={(tp+tn)/len(ys):.3f} prec={prec:.3f} "
          f"rec={rec:.3f} esp={tn/(tn+fp):.3f} F1={f1:.3f} AUC={auc(ys,ps):.3f} "
          f"Brier={brier:.4f}  (TP={tp} FP={fp} FN={fn} TN={tn})")
