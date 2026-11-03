#!/usr/bin/env python3
"""
Bateria de validacao: Jev (TypeSafe) x heuristica deterministica do SVI-AC.

Tarefa binaria: "este texto veicula desinformacao em saude?"
  y=1  claim verificada como FALSA por checadora
  y=0  manchete legitima do SVI-AC ou claim verificada como VERDADEIRA

Duas regras de decisao para o Jev:
  R1 (noul)   - corte em 0.5 na probabilidade que o noul devolve
  R2 (choice) - argmax da pergunta Choice (propaga / desmente / nao_trata)

Metricas: matriz de confusao, acuracia, precisao, revocacao, especificidade,
F1, AUC-ROC, Brier e ECE (calibracao), por subgrupo.
"""
import concurrent.futures as cf
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
SVI = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(SVI, "scripts"))

URL = "https://api.typesafe.ai/v1/systemone"
MODELO = "jev-latest"
WORKERS = 8

INSTRUCAO_NOUL = (
    "O texto afirma ou endossa, como se fosse verdadeira, uma afirmacao falsa "
    "ou enganosa sobre saude, vacinas, medicamentos, diagnosticos ou pandemia. "
    "Considere apenas o que o texto sustenta. NAO conta como desinformacao "
    "quando o texto desmente, checa, corrige ou reporta a afirmacao como falsa, "
    "sem prova ou sem base cientifica."
)
INSTRUCAO_CHOICE = "Qual o papel do texto em relacao a desinformacao em saude"

CRITERIOS = {
    "propaga": "Afirma ou endossa como verdadeira uma alegacao falsa ou enganosa",
    "desmente": "Desmente, checa, corrige ou reporta a alegacao como falsa/sem base",
    "nao_trata": "Noticia ou informacao legitima que nao veicula nem checa alegacao falsa",
}

PERGUNTAS = {
    "desinformacao": {"type": "noul", "instructions": INSTRUCAO_NOUL},
    "papel": {"type": "choice", "instructions": INSTRUCAO_CHOICE,
              "criteria": CRITERIOS},
}


def chamar(payload, tentativas=3):
    corpo = json.dumps(payload).encode()
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                URL, data=corpo,
                headers={"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))


def avaliar_item(item):
    resp = chamar({"state": item["texto"], "model": MODELO,
                   "questions": PERGUNTAS})
    a = resp["answers"]
    return {
        "id": item["id"], "y": int(item["y"]), "origem": item["origem"],
        "subgrupo": item["subgrupo"], "tema": item["tema"],
        "p_desinfo": a["desinformacao"]["noul"],
        "papel": a["papel"]["choice"],
        "papel_conf": a["papel"]["confidence"],
        "tokens_in": resp["usage"]["input_tokens"],
    }


# ---------- baseline deterministico (logica de producao do SVI) ----------
def preparar_baseline():
    import sqlite3
    norm = lambda s: "".join(
        c for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c))
    try:
        from boatos import match_boato
        import analise
        sinais = getattr(analise, "SINAIS_CHECAGEM", [])
    except Exception as e:
        print("AVISO: baseline indisponivel:", e)
        return None
    sinais = [norm(s) for s in sinais]
    caminho = os.environ.get(
        "SVI_DB_PATH", "/home/marc/.hermes/data/infodemia/infodemia.db")
    conn = sqlite3.connect(caminho)

    def baseline(texto):
        t = norm(texto)
        if any(s in t for s in sinais):
            return 0                    # checagem explicita -> nao propaga
        return 1 if match_boato(texto, conn) else 0
    return baseline


# ---------- metricas ----------
def auc(ys, ps):
    """AUC-ROC por Mann-Whitney (sem sklearn)."""
    pares = sorted(zip(ps, ys))
    n1 = sum(ys)
    n0 = len(ys) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    rank, i, soma_ranks_pos = 1, 0, 0.0
    while i < len(pares):
        j = i
        while j + 1 < len(pares) and pares[j + 1][0] == pares[i][0]:
            j += 1
        rank_medio = (rank + rank + (j - i)) / 2
        for k in range(i, j + 1):
            if pares[k][1] == 1:
                soma_ranks_pos += rank_medio
        rank += (j - i + 1)
        i = j + 1
    return (soma_ranks_pos - n1 * (n1 + 1) / 2) / (n1 * n0)


def matriz(ys, ps, corte=0.5):
    tp = sum(1 for y, p in zip(ys, ps) if y == 1 and p >= corte)
    fp = sum(1 for y, p in zip(ys, ps) if y == 0 and p >= corte)
    fn = sum(1 for y, p in zip(ys, ps) if y == 1 and p < corte)
    tn = sum(1 for y, p in zip(ys, ps) if y == 0 and p < corte)
    return tp, fp, fn, tn


def metricas(ys, ps, rotulo=""):
    n = len(ys)
    if not n:
        return None
    tp, fp, fn, tn = matriz(ys, ps)
    acc = (tp + tn) / n
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    esp = tn / (tn + fp) if tn + fp else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec and rec and prec == prec and rec == rec else float("nan")
    brier = sum((p - y) ** 2 for y, p in zip(ys, ps)) / n

    # ECE com 10 bins
    bins = defaultdict(list)
    for y, p in zip(ys, ps):
        bins[min(int(p * 10), 9)].append((y, p))
    ece = 0.0
    for b, itens in bins.items():
        conf = sum(p for _, p in itens) / len(itens)
        acerto = sum(y for y, _ in itens) / len(itens)
        ece += len(itens) / n * abs(conf - acerto)

    return dict(rotulo=rotulo, n=n, tp=tp, fp=fp, fn=fn, tn=tn, acc=acc,
                prec=prec, rec=rec, esp=esp, f1=f1, auc=auc(ys, ps),
                brier=brier, ece=ece)


def imprime(m):
    if not m:
        return
    print(f"\n--- {m['rotulo']}  (n={m['n']})")
    print(f"    TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}")
    print(f"    acuracia={m['acc']:.3f}  precisao={m['prec']:.3f}  "
          f"revocacao={m['rec']:.3f}  especificidade={m['esp']:.3f}  F1={m['f1']:.3f}")
    print(f"    AUC={m['auc']:.3f}  Brier={m['brier']:.4f}  ECE={m['ece']:.4f}")


def main():
    with open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8") as f:
        itens = list(csv.DictReader(f))
    print(f"bateria: {len(itens)} itens")

    cache = os.path.join(AQUI, "resultados_jev.csv")
    if os.path.exists(cache) and "--recache" not in sys.argv:
        with open(cache, encoding="utf-8") as f:
            res = list(csv.DictReader(f))
        for r in res:
            r["y"] = int(r["y"])
            r["p_desinfo"] = float(r["p_desinfo"])
            r["papel_conf"] = float(r["papel_conf"])
            r["tokens_in"] = int(r["tokens_in"])
        print(f"cache: {len(res)} resultados carregados de resultados_jev.csv "
              f"(use --recache para chamar a API de novo)")
    else:
        t0 = time.perf_counter()
        res = []
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for i, r in enumerate(ex.map(avaliar_item, itens), 1):
                res.append(r)
                if i % 50 == 0:
                    print(f"  {i}/{len(itens)} ({time.perf_counter()-t0:.0f}s)")
        dt = time.perf_counter() - t0
        print(f"concluido em {dt:.0f}s ({len(res)/dt:.1f} req/s)")
        with open(cache, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
            w.writeheader()
            w.writerows(res)

    ys = [r["y"] for r in res]
    p_noul = [r["p_desinfo"] for r in res]
    p_choice = [1.0 if r["papel"] == "propaga" else 0.0 for r in res]

    print("\n===== JEV =====")
    imprime(metricas(ys, p_noul, "Jev / regra noul (corte 0.5)"))
    imprime(metricas(ys, p_choice, "Jev / regra choice (propaga)"))

    base = preparar_baseline()
    if base:
        p_base = [base(it["texto"]) for it in itens]
        imprime(metricas(ys, p_base, "heuristica SVI (producao)"))

    print("\n===== por subgrupo =====")
    grupos = defaultdict(lambda: ([], []))
    for r in res:
        ys_g, ps_g = grupos[r["subgrupo"]]
        ys_g.append(r["y"]); ps_g.append(r["p_desinfo"])
    for k, (yg, pg) in sorted(grupos.items()):
        m = metricas(yg, pg, f"{k} (noul)")
        if m:
            print(f"  {k:22s} n={m['n']:4d} acerto={m['acc']:.3f} "
                  f"p_medio={sum(pg)/len(pg):.3f}  y_medio={sum(yg)/len(yg):.3f}")

    print("\n===== por tema =====")
    for tema in ("vacina_pandemia", "outros_saude"):
        sub = [r for r in res if r["tema"] == tema]
        if sub:
            m = metricas([r["y"] for r in sub], [r["p_desinfo"] for r in sub],
                         f"{tema} (noul)")
            imprime(m)

    print("\n===== falso positivo: manchetes do SVI marcadas como desinformacao =====")
    fp = [r for r in res if r["y"] == 0 and r["p_desinfo"] >= 0.5]
    fp.sort(key=lambda r: -r["p_desinfo"])
    for r in fp[:15]:
        txt = next(i["texto"] for i in itens if i["id"] == r["id"])
        print(f"  p={r['p_desinfo']:.2f} [{r['subgrupo']}] {txt[:95]}")

    print("\n===== falso negativo: desinformacao real nao detectada =====")
    fn = [r for r in res if r["y"] == 1 and r["p_desinfo"] < 0.5]
    fn.sort(key=lambda r: r["p_desinfo"])
    for r in fn[:15]:
        txt = next(i["texto"] for i in itens if i["id"] == r["id"])
        print(f"  p={r['p_desinfo']:.2f} {txt[:95]}")

    tot_in = sum(r["tokens_in"] for r in res)
    print(f"\ntokens de entrada: {tot_in:,}  (~US$ {tot_in*0.042/1e6:.5f})")


if __name__ == "__main__":
    main()
