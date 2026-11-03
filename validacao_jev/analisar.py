#!/usr/bin/env python3
"""
Analise critica da bateria: separa o que e erro do Jev do que e defeito do rotulo.

Achado: boa parte dos "positivos" coletados do G1 Fato ou Fake sao da forma
"E #FAKE que [foto|video|imagem] mostre X". Ao remover o prefixo do veredito,
sobra uma DESCRICAO de midia, nao uma afirmacao falsa sobre saude. Sao casos de
autenticidade de midia, nao de desinformacao sanitaria -> rotulo invalido para
a tarefa. Este script quantifica e refaz as metricas sem eles.
"""
import csv
import os
import re
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))

MIDIA = re.compile(
    r"\b(foto|fotos|v[ií]deo|v[ií]deos|imagem|imagens|[aá]udio|print|prints|"
    r"cartaz|panfleto|postagem|publica[çc][ãa]o|mensagem|\u00e1udio)\b",
    re.IGNORECASE)
MIDIA_VERBO = re.compile(r"\b(mostr\w*|veicul\w*|seja|gravad\w*|filmad\w*|"
                         r"exib\w*|circul\w*)\b", re.IGNORECASE)


def e_checagem_de_midia(texto):
    return bool(MIDIA.search(texto) and MIDIA_VERBO.search(texto))


def auc(ys, ps):
    pares = sorted(zip(ps, ys))
    n1 = sum(ys); n0 = len(ys) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    rank, i, soma = 1, 0, 0.0
    while i < len(pares):
        j = i
        while j + 1 < len(pares) and pares[j + 1][0] == pares[i][0]:
            j += 1
        media_rank = (rank + rank + (j - i)) / 2
        for k in range(i, j + 1):
            if pares[k][1] == 1:
                soma += media_rank
        rank += (j - i + 1)
        i = j + 1
    return (soma - n1 * (n1 + 1) / 2) / (n1 * n0)


def metricas(ys, ps, corte=0.5):
    n = len(ys)
    tp = sum(1 for y, p in zip(ys, ps) if y == 1 and p >= corte)
    fp = sum(1 for y, p in zip(ys, ps) if y == 0 and p >= corte)
    fn = sum(1 for y, p in zip(ys, ps) if y == 1 and p < corte)
    tn = sum(1 for y, p in zip(ys, ps) if y == 0 and p < corte)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec == prec and rec == rec and (prec + rec) else float("nan")
    brier = sum((p - y) ** 2 for y, p in zip(ys, ps)) / n
    bins = defaultdict(list)
    for y, p in zip(ys, ps):
        bins[min(int(p * 10), 9)].append((y, p))
    ece = sum(len(v) / n * abs(sum(p for _, p in v) / len(v) - sum(y for y, _ in v) / len(v))
              for v in bins.values())
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, acc=(tp + tn) / n, prec=prec,
                rec=rec, esp=tn / (tn + fp) if tn + fp else float("nan"),
                f1=f1, auc=auc(ys, ps), brier=brier, ece=ece)


def linha(m, rot):
    print(f"  {rot:38s} n={m['n']:4d} acc={m['acc']:.3f} prec={m['prec']:.3f} "
          f"rec={m['rec']:.3f} esp={m['esp']:.3f} F1={m['f1']:.3f} "
          f"AUC={m['auc']:.3f} Brier={m['brier']:.4f} ECE={m['ece']:.4f}")


def main():
    itens = {r["id"]: r for r in csv.DictReader(
        open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8"))}
    res = [r for r in csv.DictReader(
        open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))]
    for r in res:
        r["y"] = int(r["y"]); r["p_desinfo"] = float(r["p_desinfo"])
        r["texto"] = itens[r["id"]]["texto"]
        r["checagem_midia"] = e_checagem_de_midia(r["texto"])

    pos_midia = [r for r in res if r["y"] == 1 and r["checagem_midia"]]
    print(f"positivos totais: {sum(r['y'] for r in res)}")
    print(f"positivos que sao checagem de MIDIA (rotulo invalido p/ a tarefa): {len(pos_midia)}")
    print("  exemplos:")
    for r in pos_midia[:6]:
        print(f"    p={r['p_desinfo']:.2f}  {r['texto'][:88]}")

    limpos = [r for r in res if not (r["y"] == 1 and r["checagem_midia"])]
    print(f"\nbateria limpa: {len(limpos)} itens | positivos={sum(r['y'] for r in limpos)}")

    print("\n=== METRICAS ===")
    linha(metricas([r["y"] for r in res], [r["p_desinfo"] for r in res]),
          "bruta (todas as 412)")
    linha(metricas([r["y"] for r in limpos], [r["p_desinfo"] for r in limpos]),
          "limpa (sem checagem de midia)")
    linha(metricas([r["y"] for r in limpos if r["tema"] == "vacina_pandemia"],
                   [r["p_desinfo"] for r in limpos if r["tema"] == "vacina_pandemia"]),
          "limpa / vacina-pandemia")

    # populacao de producao: as 187 manchetes reais do SVI
    svi = [r for r in res if r["origem"] == "svi_ac"]
    print(f"\n=== POPULACAO DE PRODUCAO (manchetes reais do SVI, n={len(svi)}, todas y=0) ===")
    fp = [r for r in svi if r["p_desinfo"] >= 0.5]
    print(f"  Jev sinalizou como desinformacao: {len(fp)}/{len(svi)} "
          f"({100*len(fp)/len(svi):.1f}%)")
    for r in sorted(fp, key=lambda r: -r["p_desinfo"]):
        print(f"    p={r['p_desinfo']:.2f} {r['texto'][:92]}")

    # curva de confiabilidade (noul, bateria limpa)
    print("\n=== CALIBRACAO (noul, bateria limpa) ===")
    print("  bin      n   p_medio  y_medio   gap")
    bins = defaultdict(list)
    for r in limpos:
        bins[min(int(r["p_desinfo"] * 10), 9)].append(r)
    for b in sorted(bins):
        v = bins[b]
        pm = sum(r["p_desinfo"] for r in v) / len(v)
        ym = sum(r["y"] for r in v) / len(v)
        print(f"  {b/10:.1f}-{b/10+0.1:.1f} {len(v):4d}   {pm:.3f}    {ym:.3f}   {pm-ym:+.3f}")

    # varredura de corte
    print("\n=== VARREDURA DE CORTE (bateria limpa) ===")
    for c in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        m = metricas([r["y"] for r in limpos], [r["p_desinfo"] for r in limpos], c)
        print(f"  corte {c:.1f}: acc={m['acc']:.3f} prec={m['prec']:.3f} "
              f"rec={m['rec']:.3f} F1={m['f1']:.3f}")

    # falsos negativos remanescentes
    print("\n=== FALSOS NEGATIVOS remanescentes (bateria limpa, corte 0.5) ===")
    fn = sorted([r for r in limpos if r["y"] == 1 and r["p_desinfo"] < 0.5],
                key=lambda r: r["p_desinfo"])
    print(f"  total: {len(fn)}")
    for r in fn[:20]:
        print(f"    p={r['p_desinfo']:.2f} {r['texto'][:92]}")


if __name__ == "__main__":
    main()
