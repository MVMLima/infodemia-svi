#!/usr/bin/env python3
"""Comparativo final Jev x DeepSeek-V4-Flash na MESMA bateria limpa."""
import csv, json, os, sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from analisar import e_checagem_de_midia, metricas   # metricas de analisar respeita o corte

itens = {r["id"]: r for r in csv.DictReader(
    open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8"))}
jev = {r["id"]: r for r in csv.DictReader(
    open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))}
ds = {r["id"]: r for r in (json.loads(l) for l in
      open(os.path.join(AQUI, "resultados_deepseek.jsonl"), encoding="utf-8") if l.strip())}

limpos = [i for i in itens.values()
          if not (int(i["y"]) == 1 and e_checagem_de_midia(i["texto"]))]
limpos.sort(key=lambda i: i["id"])
print(f"bateria limpa: {len(limpos)} itens | "
      f"positivos={sum(int(i['y']) for i in limpos)} "
      f"negativos={sum(1 for i in limpos if int(i['y']) == 0)}")

ys = [int(i["y"]) for i in limpos]
P = {
    "Jev / noul (limiar 0.5)":      [float(jev[i["id"]]["p_desinfo"]) for i in limpos],
    "Jev / choice propaga":         [1.0 if jev[i["id"]]["papel"] == "propaga" else 0.0 for i in limpos],
    "DeepSeek / prob (limiar 0.5)": [float(ds[i["id"]]["p_desinfo"]) for i in limpos],
    "DeepSeek / choice propaga":    [1.0 if ds[i["id"]]["papel"] == "propaga" else 0.0 for i in limpos],
}

print("\n=== METRICAS (bateria limpa, n=%d) ===" % len(limpos))
print(f"{'regra':30s} {'acc':>6} {'prec':>6} {'rec':>6} {'esp':>6} {'F1':>6} {'AUC':>6} {'Brier':>7} {'ECE':>6}")
for nome, ps in P.items():
    m = metricas(ys, ps)
    print(f"{nome:30s} {m['acc']:6.3f} {m['prec']:6.3f} {m['rec']:6.3f} "
          f"{m['esp']:6.3f} {m['f1']:6.3f} {m['auc']:6.3f} {m['brier']:7.4f} {m['ece']:6.4f}")

print("\n=== VARREdura DE LIMIAR ===")
for nome in ("Jev / noul (limiar 0.5)", "DeepSeek / prob (limiar 0.5)"):
    ps = P[nome]
    linha = []
    for c in (0.3, 0.4, 0.5, 0.6, 0.7):
        m = metricas(ys, ps, c)
        linha.append(f"{c:.1f}: acc={m['acc']:.3f} rec={m['rec']:.3f} F1={m['f1']:.3f}")
    print(f"  {nome.split('/')[0].strip():9s} " + " | ".join(linha))

print("\n=== POPULACAO DE PRODUCAO (manchetes reais do SVI) ===")
svi = [i for i in limpos if i["origem"] == "svi_ac"]
for nome, ps in P.items():
    if "choice" in nome:
        continue
    n_fp = sum(1 for i, p in zip(limpos, ps) if i["origem"] == "svi_ac" and p >= 0.5)
    print(f"  {nome:30s} {n_fp}/{len(svi)} sinalizadas ({100*n_fp/len(svi):.1f}%)")

print("\n=== CALIBRACAO: modelo sabe quando esta certo? ===")
print(f"{'faixa':>10} | {'nJ':>4} {'Jev p_med':>9} {'y_med':>6} | {'nD':>4} {'DS p_med':>8} {'y_med':>6}")
pj, pd_ = P["Jev / noul (limiar 0.5)"], P["DeepSeek / prob (limiar 0.5)"]
for lo in [i/10 for i in range(10)]:
    idx = [k for k, p in enumerate(pj) if lo <= p < lo + 0.1]
    idx2 = [k for k, p in enumerate(pd_) if lo <= p < lo + 0.1]
    if not idx and not idx2:
        continue
    fj = (f"{sum(pj[k] for k in idx)/len(idx):9.3f} "
          f"{sum(ys[k] for k in idx)/len(idx):6.3f}") if idx else " " * 16
    fd = (f"{sum(pd_[k] for k in idx2)/len(idx2):8.3f} "
          f"{sum(ys[k] for k in idx2)/len(idx2):6.3f}") if idx2 else " " * 15
    print(f"{lo:10.1f} | {len(idx):4d} {fj} | {len(idx2):4d} {fd}")

print("\n=== CONCORDANCIA ENTRE OS MODELOS (decisao binaria) ===")
dec_j = [1 if p >= 0.5 else 0 for p in pj]
dec_d = [1 if p >= 0.5 else 0 for p in pd_]
conc = [k for k in range(len(ys)) if dec_j[k] == dec_d[k]]
div = [k for k in range(len(ys)) if dec_j[k] != dec_d[k]]
ac_conc = sum(1 for k in conc if dec_j[k] == ys[k])
ac_div_j = sum(1 for k in div if dec_j[k] == ys[k])
ac_div_d = sum(1 for k in div if dec_d[k] == ys[k])
print(f"  concordam em {len(conc)}/{len(ys)} itens ({100*len(conc)/len(ys):.1f}%) "
      f"-> acerto nesses: {ac_conc}/{len(conc)} = {ac_conc/len(conc):.3f}")
print(f"  divergem em {len(div)} itens ({100*len(div)/len(ys):.1f}%) "
      f"-> acerto Jev {ac_div_j}/{len(div)}, DeepSeek {ac_div_d}/{len(div)}")
print(f"  erro conjunto  = {sum(1 for k in range(len(ys)) if dec_j[k]!=ys[k] or dec_d[k]!=ys[k])} "
      f"de {len(ys)} -> acerto combinado "
      f"{(len(ys)-sum(1 for k in range(len(ys)) if dec_j[k]!=ys[k] or dec_d[k]!=ys[k]))/len(ys):.3f}")

print("\n=== CUSTO ===")
tj = sum(float(jev[i["id"]]["tokens_in"]) for i in limpos)
print(f"  Jev:      {tj:,.0f} tokens entrada | saida gratuita")
print(f"  DeepSeek: {sum(ds[i['id']]['tokens_in'] for i in limpos):,} entrada | "
      f"{sum(ds[i['id']]['tokens_out'] for i in limpos):,} saida (inclui raciocinio)")
