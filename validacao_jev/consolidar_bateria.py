#!/usr/bin/env python3
"""
Consolida a bateria final: casos reais rotulados para a tarefa binaria
"este texto veicula desinformacao em saude?".

  positivo (1) = claim com veredito FALSO de checadora  -> desinformacao
  negativo (0) = manchete legitima do SVI-AC  OU  claim com veredito VERDADEIRO

Saida: bateria_final.csv  (id, texto, y, origem, subgrupo, tema)
  tema = vacina_pandemia  -> dentro do escopo monitorado pelo SVI
         outros_saude     -> desinformacao de saude fora do escopo vacinal
"""
import csv
import os
import re
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))

# Escopo: saude publica / vacinas / pandemia / tratamento / vetores
SAUDE = re.compile(
    r"vacina|vacinaç|vacinac|imuniz|imuniza|covid|corona|pandemia|dengue|"
    r"sarampo|gripe|influenza|cloroquina|ivermectina|rem[eé]dio|medicament|"
    r"sa[uú]de|hospital|sus\b|anvisa|oms\b|v[ií]rus|hantav|nipah|doen[çc]a|"
    r"morte|mortalidade|[oó]bito|c[aâ]ncer|autismo|chip|dna|efeito colateral|"
    r"terapia|tratamento|cura|meningite|hpv|var[ií]ola|alzheimer|"
    r"m[aá]scara|pr[oó]polis|metanol|diabet|mosquito|repelente|intoxica|"
    r"pulm[aã]o|respirat|sangue|transplante|cirurgia|obesidade|dieta",
    re.IGNORECASE)

TEMA = re.compile(r"vacina|vacinac|imuniz|covid|corona|pandemia",
                  re.IGNORECASE)

# Ruido de escopo que escapou do filtro por palavra
BLOQUEIO = re.compile(r"toyota|lula|bolsonaro|taylor swift|copa|esc[oó]cia|"
                      r"onu ap[oó]s|arquibancada", re.IGNORECASE)


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def chave(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


def tema(s):
    return "vacina_pandemia" if TEMA.search(s) else "outros_saude"


def carrega(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    chec = carrega(os.path.join(AQUI, "checagens.csv"))
    bat = carrega(os.path.join(AQUI, "bateria.csv"))
    itens, vistos = [], set()

    def add(ident, texto, y, origem, sub):
        k = chave(texto)
        if k in vistos:
            return False
        vistos.add(k)
        itens.append(dict(id=ident, texto=texto, y=y, origem=origem,
                          subgrupo=sub, tema=tema(texto)))
        return True

    n_pos = n_verd = n_svi = 0
    for c in chec:
        if c["rotulo"] != "propagacao" or not SAUDE.search(c["texto"]):
            continue
        if BLOQUEIO.search(c["texto"]):
            continue
        if add(f"chk{n_pos:04d}", c["texto"], 1, "checadora", "veredito_falso"):
            n_pos += 1

    for c in chec:
        if c["rotulo"] != "verdadeiro" or not SAUDE.search(c["texto"]):
            continue
        if add(f"verd{n_verd:03d}", c["texto"], 0, "checadora", "veredito_verdadeiro"):
            n_verd += 1

    for b in bat:
        if b["rotulo"] != "nenhuma":
            continue
        if add(f"svi{b['id']}", b["texto"], 0, "svi_ac", "manchete_legitima"):
            n_svi += 1

    saida = os.path.join(AQUI, "bateria_final.csv")
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "texto", "y", "origem",
                                          "subgrupo", "tema"])
        w.writeheader()
        w.writerows(itens)

    pos = sum(i["y"] for i in itens)
    print(f"bateria_final.csv: {len(itens)} itens | positivos={pos} negativos={len(itens)-pos}")
    print(f"  positivos (veredito FALSO)...: {n_pos}")
    print(f"  negativos (veredito VERDADE.): {n_verd}")
    print(f"  negativos (manchete SVI).....: {n_svi}")
    from collections import Counter
    print("\npor tema:")
    for (tema_, y), v in sorted(Counter((i["tema"], i["y"]) for i in itens).items()):
        print(f"  {tema_:15s} y={y}: {v}")

    desc = [c["texto"] for c in chec if not SAUDE.search(c["texto"])]
    print(f"\nDescartados pelo filtro de escopo: {len(desc)}")
    for d in desc[:15]:
        print("   x", d[:95])


if __name__ == "__main__":
    main()
