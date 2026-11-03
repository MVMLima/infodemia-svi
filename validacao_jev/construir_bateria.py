#!/usr/bin/env python3
"""
Constroi a bateria de validacao Jev x heuristica do SVI-AC.

Fonte: banco de producao do SVI (214 mencoes reais coletadas 13/07-17/09/2026).
Rotulo (3 classes), decido por leitura das manchetes:

  checagem  - o texto DESMENTE / verifica explicitamente uma narrativa falsa
              (fact-check declarado ou explicativo de debunk)
  nenhuma   - noticia legitima; nao trata de narrativa de desinformacao
  revisar   - caso de fronteira: reporta a narrativa / marca como sem prova,
              mas nao e um fact-check declarado. EXCLUIDO da metrica principal.

Fonte do rotulo fica gravada em `fonte_rotulo`:
  veredito_no_titulo - o proprio titulo carrega o veredito ("E #FAKE que...")
  curadoria          - lido e classificado manualmente
"""
import csv
import os
import re
import sqlite3
import unicodedata

DB = os.environ.get("SVI_DB_PATH", "/home/marc/.hermes/data/infodemia/infodemia.db")
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bateria.csv")

# --- rotulos de curadoria (ids do banco -> classe, motivo) ---
CHECAGEM_IDS = {
    65: "explicativo de debunk: desmente que vacina altere o DNA",
    64: "explicativo: origem do mito vacina-autismo",
    81: "explicativo: desmente alteracao de DNA",
}
REVISAR_IDS = {
    62: "reporta associacao sem provas (nao e fact-check declarado)",
    66: "reporta o mito do chip como causa de hesitacao",
    510: "reporta associacao sem base cientifica por terceiro",
    525: "duplicata de 510",
}

MARCADOR = re.compile(
    r"#fake|é fake|e fake|fato ou fake|checagem|desmentid|é mentira|"
    r"não é verdade|nao e verdade|fake news|é falso|e falso|não mexe",
    re.IGNORECASE)


def normaliza(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def main():
    conn = sqlite3.connect(DB)
    linhas = list(conn.execute(
        "select id, titulo, date, fonte from mencoes order by id"))
    conn.close()

    vistos, itens = set(), []
    for rid, titulo, data, fonte in linhas:
        chave = normaliza(titulo)
        if chave in vistos:
            continue          # dedup por titulo normalizado (o corpus tem
        vistos.add(chave)     # a mesma noticia em varios dominios)

        if rid in CHECAGEM_IDS:
            rotulo, prov, obs = "checagem", "curadoria", CHECAGEM_IDS[rid]
        elif rid in REVISAR_IDS:
            rotulo, prov, obs = "revisar", "curadoria", REVISAR_IDS[rid]
        elif MARCADOR.search(titulo):
            rotulo, prov, obs = "checagem", "veredito_no_titulo", "marcador de checagem no titulo"
        else:
            rotulo, prov, obs = "nenhuma", "curadoria", ""

        itens.append(dict(id=rid, data=data, fonte=fonte or "",
                          texto=titulo, rotulo=rotulo,
                          fonte_rotulo=prov, obs=obs))

    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "data", "fonte", "texto",
                                          "rotulo", "fonte_rotulo", "obs"])
        w.writeheader()
        w.writerows(itens)

    from collections import Counter
    print("bateria gravada:", SAIDA)
    print("itens:", len(itens))
    for k, v in Counter(i["rotulo"] for i in itens).most_common():
        print(f"  {k}: {v}")
    print("\npositivos e casos de fronteira:")
    for i in itens:
        if i["rotulo"] != "nenhuma":
            print(f"  [{i['rotulo']:8s}] id={i['id']:4d} {i['texto'][:95]}")


if __name__ == "__main__":
    main()
