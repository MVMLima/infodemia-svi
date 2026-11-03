#!/usr/bin/env python3
"""Auditoria independente v3 — EXCLI-25-1437-s-001.xlsx.
Confere a tabela 'Reproduction checks' do proprio codebook dos autores.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, timedelta

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NSR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
PATH = "/tmp/excli_x/EXCLI-25-1437-s-001.xlsx"
HEB_MALE = "\u05d6\u05db\u05e8"    # זכר
HEB_FEM = "\u05e0\u05e7\u05d1\u05d4"  # נקבה


def col_index(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n


def load(z):
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(f"{NS}t"))
                  for si in root.findall(f"{NS}si")]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rmap = {r.get("Id"): r.get("Target") for r in rels.findall(f"{PKG}Relationship")}
    out = {}
    for sh in wb.find(f"{NS}sheets").findall(f"{NS}sheet"):
        tgt = rmap.get(sh.get(f"{NSR}id"), "") or ""
        if not tgt.startswith("xl/"):
            tgt = "xl/" + tgt.lstrip("/")
        root = ET.fromstring(z.read(tgt))
        rows = []
        for r in root.iter(f"{NS}row"):
            cells = {}
            for c in r.findall(f"{NS}c"):
                ci = col_index(c.get("r"))
                if c.get("t") == "inlineStr":
                    isn = c.find(f"{NS}is")
                    val = "".join(x.text or "" for x in isn.iter(f"{NS}t")) if isn is not None else ""
                else:
                    v = c.find(f"{NS}v")
                    val = v.text if v is not None and v.text is not None else ""
                    if c.get("t") == "s" and val != "":
                        try:
                            val = shared[int(val)]
                        except (ValueError, IndexError):
                            pass
                cells[ci] = val
            if cells:
                rows.append([cells.get(i, "") for i in range(1, max(cells) + 1)])
        out[sh.get("name")] = rows
    return out


def fnum(x):
    try:
        return float(str(x).replace(",", "."))
    except (ValueError, TypeError):
        return None


def xl_date(serial):
    try:
        return date(1899, 12, 30) + timedelta(days=int(float(serial)))
    except (ValueError, TypeError):
        return None


def main():
    with zipfile.ZipFile(PATH) as z:
        sh = load(z)
    H, D = sh["Hospitalizations"], sh["Deaths"]
    hdr, hbody = H[0], H[1:]
    ci = {n: i for i, n in enumerate(hdr)}

    # linha em branco final deve sair; todo o resto e' registro de origem
    registros = [r for r in hbody if any(str(c).strip() for c in r)]
    print(f"linhas com conteudo (registros de origem): {len(registros)}   [codebook: 532]")

    sem_num = [r for r in registros if not str(r[ci["Case Number מספר"]]).strip()]
    print(f"registros sem Case Number: {len(sem_num)}  (iniciais anonimizadas)")
    for r in sem_num:
        print("   idade:", r[ci["Age גיל"]], "| sexo:", r[ci["Gender מגדר"]],
              "| myocarditis_pericarditis:", r[ci["myocarditis_pericarditis"]],
              "| meaningful_medical_history:", r[ci["meaningful_medical_history"]])

    analitico = [r for r in registros
                 if str(r[ci["Case Number מספר"]]).strip() != "343"]
    print(f"\n>> DATASET ANALITICO = {len(analitico)}   [codebook: 531]")

    def g(r, col):
        return str(r[ci[col]]).strip()

    myo = Counter(g(r, "myocarditis_pericarditis") for r in analitico)
    n_myo = myo["1"] + myo["2"]
    print("\n--- CONFUSAO DOS NUMEROS DO ARTIGO vs PLANILHA ---")
    checks = [
        ("myocarditis_pericarditis = 0", myo["0"], 281),
        ("myocarditis_pericarditis = 1", myo["1"], 248),
        ("myocarditis_pericarditis = 2", myo["2"], 2),
        ("miocardite/pericardite (1 ou 2)", n_myo, 250),
    ]
    st = Counter(g(r, "patient_status") for r in analitico)
    checks += [
        ("patient_status = 0 (alta)", st["0"], 502),
        ("patient_status = 1 (internado)", st["1"], 14),
        ("patient_status = 2 (obito)", st["2"], 6),
        ("patient_status = 9 (indefinido)", st["9"], 9),
    ]

    idades = [fnum(r[ci["Age גיל"]]) for r in analitico]
    validas = [a for a in idades if a is not None and not (a >= 120)]
    u30_idx = [i for i, a in enumerate(idades) if a is not None and a < 30]
    u30 = [analitico[i] for i in u30_idx]
    u30_myo = [r for r in u30 if g(r, "myocarditis_pericarditis") in ("1", "2")]
    u30_sem_hist = [r for r in u30 if g(r, "meaningful_medical_history") == "0"]
    inter = [r for r in u30_sem_hist if g(r, "myocarditis_pericarditis") in ("1", "2")]
    masc = [r for r in inter if g(r, "Gender מגדר") == HEB_MALE]

    checks += [
        ("com idade valida (<120)", len(validas), 530),
        ("pacientes < 30 anos", len(u30), 211),
        ("<30 com miocardite/pericardite", len(u30_myo), 151),
        ("<30 com meaningful_medical_history = 0", len(u30_sem_hist), 134),
        ("miocardite/pericardite nesse subgrupo", len(inter), 99),
        ("homens nesse subgrupo", len(masc), 90),
    ]

    t = [fnum(r[ci["time_from_vaccination_days"]]) for r in analitico]
    tv = sorted(x for x in t if x is not None)
    med = tv[len(tv) // 2] if len(tv) % 2 else (tv[len(tv) // 2 - 1] + tv[len(tv) // 2]) / 2
    q1, q3 = tv[len(tv) // 4], tv[(3 * len(tv)) // 4]
    checks += [
        ("time_from_vaccination_days validos", len(tv), 529),
    ]

    ok = 0
    for nome, obtido, esperado in checks:
        flag = "OK " if obtido == esperado else "DIF"
        ok += obtido == esperado
        print(f"  [{flag}] {nome:46s} planilha={obtido:<5} codebook={esperado}")
    print(f"\n  >>> {ok}/{len(checks)} conferencias batem com a tabela dos autores")

    print(f"\n  mediana tempo vacinacao->evento: {med:.0f} dias (IQR {q1:.0f}-{q3:.0f})  [artigo: 5 (3-15)]")

    datas = sorted(d for d in (xl_date(r[ci["Date Reported to Pfizer תאריך דיווח לפייזר"]])
                               for r in analitico) if d)
    print(f"  reportes a Pfizer: {len(set(datas))} datas distintas  [artigo: 36]")
    print(f"  janela: {min(datas)} a {max(datas)}   [artigo: 25/03/2021 a 09/05/2022]")

    # ---- obitos ----
    print("\n\n========== DEATHS ==========")
    dhdr, dbody = D[0], D[1:]
    di = {n: i for i, n in enumerate(dhdr)}
    print("colunas:", [str(c) for c in dhdr if str(c).strip()])
    dreg = [r for r in dbody if any(str(c).strip() for c in r)]
    print(f"registros de obito (linha de origem): {len(dreg)}   [codebook: 62]")
    dmyo = Counter(str(r[di["myocarditis_pericarditis"]]).strip() for r in dreg)
    print("myocarditis_pericarditis nos obitos:", dict(dmyo))

    # morte unica: 62 + 6 hospitalizacoes com obito - 1 sobreposicao
    h_died = [r for r in analitico if g(r, "patient_status") == "2"]
    print(f"hospitalizacoes com patient_status=2 (obito): {len(h_died)}")
    print(f"total de obitos unicos = 62 + {len(h_died)} - 1 = {62 + len(h_died) - 1}"
          "   [artigo: 67]")
    tid = [fnum(r[di["time_from_vaccination_days"]]) for r in dreg]
    tid = sorted(x for x in tid if x is not None)
    m2 = tid[len(tid) // 2] if len(tid) % 2 else (tid[len(tid) // 2 - 1] + tid[len(tid) // 2]) / 2
    print(f"mediana tempo vacinacao->obito: {m2:.0f} dias (n={len(tid)})  [artigo: 3 dias (IQR 1-7)]")

    # idades dos obitos
    ca = di.get("Age גיל")
    if ca is not None:
        da = [fnum(r[ca]) for r in dreg]
        da = [a for a in da if a is not None]
        sub50 = [a for a in da if a < 50]
        print(f"obitos <50 anos: {len(sub50)} de {len(da)} = {100*len(sub50)/len(da):.1f}%"
              "   [artigo: 9 de 67 = 13.4%]")


if __name__ == "__main__":
    sys.exit(main())
