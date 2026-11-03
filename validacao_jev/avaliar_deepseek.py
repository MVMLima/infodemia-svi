#!/usr/bin/env python3
"""
Mesma bateria, mesmo enunciado, modelo diferente: DeepSeek-V4-Flash.

Espelha as duas perguntas do Jev:
  R1 = probabilidade autorreportada (equivale ao `noul`)
  R2 = papel escolhido entre propaga/desmente/nao_trata (equivale ao `choice`)

ATENCAO METODOLOGICA: a probabilidade do Jev e nativa (o modelo e treinado para
devolver probabilidades calibradas). Aqui ela e *autorreportada em texto* por um
LLM generativo. Comparar as duas curvas de calibracao e comparar elicitacoes
diferentes, nao so modelos. A comparacao de decisao (acuracia/precisao/revocacao)
e direta e justa.

Retomavel: grava cada resposta em resultados_deepseek.jsonl.
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

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from avaliar import metricas, imprime          # reusa as metricas do Jev

URL = "https://api.deepseek.com/chat/completions"
MODELO = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
WORKERS = 16
MAX_TOKENS = 4000
JSONL = os.path.join(AQUI, "resultados_deepseek.jsonl")

PROMPT = """Voce classifica um texto de saude publica. Leia o texto e responda.

TEXTO:
\"\"\"{texto}\"\"\"

Definicoes:
- "propaga": O texto afirma ou endossa, como se fosse verdadeira, uma afirmacao falsa ou enganosa sobre saude, vacinas, medicamentos, diagnosticos ou pandemia. Considere apenas o que o texto sustenta. NAO conta como desinformacao quando o texto desmente, checa, corrige ou reporta a afirmacao como falsa, sem prova ou sem base cientifica.
- "desmente": O texto desmente, checa, corrige ou reporta a alegacao como falsa ou sem base.
- "nao_trata": Noticia ou informacao legitima que nao veicula nem checa alegacao falsa.

"probabilidade" = sua probabilidade (0 a 1) de que o texto veicule desinformacao (papel = "propaga").

Responda APENAS com o JSON, sem markdown e sem texto em volta:
{{"papel": "propaga" | "desmente" | "nao_trata", "probabilidade": 0.0}}"""


def chamar(texto, tentativas=3):
    corpo = json.dumps({
        "model": MODELO,
        "messages": [{"role": "user", "content": PROMPT.format(texto=texto)}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }).encode()
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                URL, data=corpo,
                headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))


def extrair(resp):
    msg = resp["choices"][0]["message"]
    bruto = (msg.get("content") or "").strip()
    bruto = re.sub(r"^```(?:json)?|```$", "", bruto, flags=re.M).strip()
    m = re.search(r"\{.*\}", bruto, re.DOTALL)
    if not m:
        raise ValueError(f"sem JSON: {bruto[:120]!r}")
    d = json.loads(m.group(0))
    papel = str(d.get("papel", "")).strip().lower()
    if papel not in ("propaga", "desmente", "nao_trata"):
        raise ValueError(f"papel invalido: {papel!r}")
    p = float(d.get("probabilidade", 0.0))
    p = min(max(p, 0.0), 1.0)
    u = resp.get("usage", {})
    return papel, p, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def avaliar_item(item):
    for tent in range(2):
        try:
            resp = chamar(item["texto"])
            papel, p, tin, tout = extrair(resp)
            return dict(id=item["id"], y=int(item["y"]), origem=item["origem"],
                        subgrupo=item["subgrupo"], tema=item["tema"],
                        p_desinfo=p, papel=papel, ok=1,
                        tokens_in=tin, tokens_out=tout)
        except Exception as e:
            if tent == 1:
                return dict(id=item["id"], y=int(item["y"]), origem=item["origem"],
                            subgrupo=item["subgrupo"], tema=item["tema"],
                            p_desinfo=0.5, papel="nao_trata", ok=0,
                            tokens_in=0, tokens_out=0, erro=str(e)[:200])


def main():
    with open(os.path.join(AQUI, "bateria_final.csv"), encoding="utf-8") as f:
        itens = list(csv.DictReader(f))

    feitos = {}
    if os.path.exists(JSONL):
        with open(JSONL, encoding="utf-8") as f:
            for linha in f:
                try:
                    r = json.loads(linha)
                    feitos[r["id"]] = r
                except Exception:
                    pass
    pendentes = [i for i in itens if i["id"] not in feitos]
    print(f"bateria: {len(itens)} | ja feitos: {len(feitos)} | pendentes: {len(pendentes)}")

    if pendentes:
        t0 = time.perf_counter()
        with open(JSONL, "a", encoding="utf-8") as fa, \
                cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for n, r in enumerate(ex.map(avaliar_item, pendentes), 1):
                fa.write(json.dumps(r, ensure_ascii=False) + "\n")
                fa.flush()
                if n % 25 == 0:
                    print(f"  {n}/{len(pendentes)} ({time.perf_counter()-t0:.0f}s)", flush=True)
        print(f"concluido em {time.perf_counter()-t0:.0f}s")

    with open(JSONL, encoding="utf-8") as f:
        res = [json.loads(l) for l in f if l.strip()]
    falhas = [r for r in res if not r.get("ok")]
    print(f"itens com resposta valida: {len(res)-len(falhas)}/{len(res)}"
          + (f" | FALHAS: {len(falhas)}" if falhas else ""))

    ys = [r["y"] for r in res]
    p_prob = [r["p_desinfo"] for r in res]
    p_choice = [1.0 if r["papel"] == "propaga" else 0.0 for r in res]

    print("\n===== DEEPSEEK-V4-FLASH =====")
    imprime(metricas(ys, p_prob, f"DeepSeek / regra probabilidade (corte 0.5)"))
    imprime(metricas(ys, p_choice, "DeepSeek / regra papel (propaga)"))

    print("\n===== comparativo (mesma bateria) =====")
    print("  metrica          Jev(noul)   Jev(choice)  DeepSeek(prob)  DeepSeek(papel)")
    for campo, nome in (("acc", "acuracia"), ("prec", "precisao"),
                        ("rec", "revocacao"), ("esp", "especificidade"),
                        ("f1", "F1"), ("auc", "AUC-ROC"), ("brier", "Brier"),
                        ("ece", "ECE")):
        vals = []
        for arq, regra in (("resultados_jev.csv", "noul"),
                           ("resultados_jev.csv", "papel"),
                           ("resultados_deepseek.jsonl", "prob"),
                           ("resultados_deepseek.jsonl", "papel")):
            caminho = os.path.join(AQUI, arq)
            if not os.path.exists(caminho):
                vals.append(float("nan")); continue
            if arq.endswith(".csv"):
                rr = list(csv.DictReader(open(caminho, encoding="utf-8")))
                yy = [int(x["y"]) for x in rr]
                pp = ([float(x["p_desinfo"]) for x in rr] if regra == "noul"
                      else [1.0 if x["papel"] == "propaga" else 0.0 for x in rr])
            else:
                yy = [x["y"] for x in res]
                pp = (p_prob if regra == "prob" else p_choice)
            vals.append(metricas(yy, pp).get(campo, float("nan")))
        print(f"  {nome:16s} {vals[0]:10.3f} {vals[1]:12.3f} {vals[2]:15.3f} {vals[3]:16.3f}")

    print("\n===== opiniao x acerto: o modelo sabe quando erra? =====")
    for nome, ps in (("probabilidade", p_prob), ("papel(propaga)", p_choice)):
        acertos = sum(1 for y, p in zip(ys, ps) if (p >= 0.5) == (y == 1))
        print(f"  {nome}: {acertos}/{len(ys)} = {acertos/len(ys):.3f}")

    print("\n===== custo em tokens =====")
    print(f"  entrada: {sum(r['tokens_in'] for r in res):,}"
          f"  saida: {sum(r['tokens_out'] for r in res):,}"
          f"  (saida inclui tokens de raciocinio)")

    print("\n===== exemplos de divergencia Jev x DeepSeek =====")
    jev = {r["id"]: r for r in csv.DictReader(
        open(os.path.join(AQUI, "resultados_jev.csv"), encoding="utf-8"))}
    textos = {i["id"]: i["texto"] for i in itens}
    d = [r for r in res
         if (r["p_desinfo"] >= 0.5) != (float(jev[r["id"]]["p_desinfo"]) >= 0.5)]
    print(f"  {len(d)} itens em que as regras de probabilidade divergem")
    for r in d[:10]:
        j = float(jev[r["id"]]["p_desinfo"])
        print(f"    y={r['y']} jev={j:.2f} ds={r['p_desinfo']:.2f} | {textos[r['id']][:82]}")


if __name__ == "__main__":
    main()
