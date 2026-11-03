#!/usr/bin/env python3
"""O gate de confianca (papel) discrimina acerto de erro nesta bateria?"""
import csv
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
res = [r for r in csv.DictReader(
    open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))]
for r in res:
    r["y"] = int(r["y"]); r["p"] = float(r["p_desinfo"])
    r["c"] = float(r["papel_conf"])
    r["acertou_choice"] = int((r["papel"] == "propaga") == (r["y"] == 1))
    r["acertou_noul"] = int((r["p"] >= 0.5) == (r["y"] == 1))

print(f"n={len(res)}\n")
print(">>> Se o gate funcionasse, a taxa de acerto subiria com a confianca.")
print(">>> Se nao funcionar, e o pitfall da opcao de abstencao.\n")
print(f"{'faixa conf':>12} {'n':>5} {'acerto choice':>14} {'acerto noul':>12} {'p_medio':>8} {'y_medio':>8}")
for lo, hi in [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.01)]:
    v = [r for r in res if lo <= r["c"] < hi]
    if not v:
        continue
    n = len(v)
    print(f"{lo:.1f}-{hi:.1f}".rjust(12) +
          f" {n:5d} {sum(r['acertou_choice'] for r in v)/n:14.3f}"
          f" {sum(r['acertou_noul'] for r in v)/n:12.3f}"
          f" {sum(r['c'] for r in v)/n:8.3f}"
          f" {sum(r['y'] for r in v)/n:8.3f}")

print("\n>>> Desempenho dos itens de BAIXA confianca (o gate mandaria p/ humano):")
baixa = [r for r in res if r["c"] < 0.6]
if baixa:
    print(f"    n={len(baixa)} ({100*len(baixa)/len(res):.1f}% da bateria)")
    print(f"    acerto noul neles: {sum(r['acertou_noul'] for r in baixa)/len(baixa):.3f}")
    erros = [r for r in res if not r["acertou_noul"]]
    print(f"    dos {len(erros)} erros do noul, quantos tem conf<0.6: "
          f"{sum(1 for r in erros if r['c'] < 0.6)}")
    print(f"    itens com conf>=0.6 que o noul errou: "
          f"{sum(1 for r in erros if r['c'] >= 0.6)}")
