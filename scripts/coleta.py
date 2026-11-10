#!/usr/bin/env python3
"""
coleta.py — Coleta de menções sobre temas de saúde (SVI-AC).

Fontes: Google News RSS + DuckDuckGo Lite (fallback).
Análise: sentimento por keyword matching (PT-BR, contexto saúde/vacina).
Output: JSON para stdout, INSERT no SQLite.

Uso: python3 coleta.py
"""
import json
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from paths import db_path

DB_PATH = db_path()
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

REGIAO = "Acre"

TERMOS = [
    "vacina", "vacinação", "imunização", "covid", "pandemia",
    "coronavírus", "vacina autismo", "chip vacina",
    "pandemia fabricada", "vacina altera dna",
]

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) HermesAgent-SVI/1.0"

# Dicionários de sentimento (contexto saúde pública / vacinação)
POSITIVO = [
    "protege", "eficaz", "segurança", "aprovação", "recomendada", "gratuito",
    "cobertura", "avanço", "proteção", "imunidade", "confiável",
    "segura", "eficácia", "controle", "queda", "redução", "melhora", "salva",
    "benefício", "prevenção", "bom resultado",
]

NEGATIVO = [
    "fraude", "morte", "reação", "grave", "perigosa", "recusa", "desconfiança",
    "mentira", "fabricada", "farsa", "boicote", "pânico", "medo", "risco",
    "fatal", "óbito", "mortes", "erro", "falha", "suspeita", "alerta",
]

NEUTRO = [
    "vacina", "dose", "campanha", "estudo", "pesquisa", "dados", "notícia",
    "secretaria", "ministério", "município", "estado", "calendário", "cartão",
    "imunização", "programa", "registro", "boletim", "informe", "coleta",
]


def web_fetch(url: str, timeout: int = 10) -> str:
    """Busca conteúdo de uma URL e retorna texto utf-8."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_news_xml(xml_texto: str) -> List[Dict]:
    """Extrai itens (título + link + data de publicação) de um XML RSS do Google News."""
    itens = []
    for item in re.findall(r"<item>(.*?)</item>", xml_texto, re.DOTALL):
        title_match = re.search(r"<title>(.*?)</title>", item)
        link_match = re.search(r"<link>(.*?)</link>", item)
        pubdate_match = re.search(r"<pubDate>(.*?)</pubDate>", item)
        if not title_match:
            continue
        titulo = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title_match.group(1)).strip()
        titulo = re.sub(r"<[^>]+>", "", titulo).strip()
        link = link_match.group(1).strip() if link_match else ""
        pubdate = pubdate_match.group(1).strip() if pubdate_match else ""
        if titulo:
            itens.append({"titulo": titulo, "url": link, "pubdate": pubdate})
    return itens


def _data_pubdate(pubdate: str) -> Optional[str]:
    """Converte pubDate RSS (RFC 822) para YYYY-MM-DD. Retorna None se inválido."""
    if not pubdate:
        return None
    try:
        # Ex: 'Sat, 02 Aug 2026 10:30:00 GMT'
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pubdate).date().isoformat()
    except Exception:
        return None


def _resolver_data(pubdate: str, hoje: str, aceitar_sem_data: bool = False):
    """
    Decide a data e a origem da data de uma menção.

    Retorna (data, fonte) ou (None, None) quando o item deve ser descartado.
    Item sem pubDate válido não é evidência de menção naquele dia: por padrão é
    descartado. Com aceitar_sem_data=True ele é mantido com a data de coleta,
    marcado como 'fallback' para permitir auditoria posterior.
    """
    data_pub = _data_pubdate(pubdate)
    if data_pub is None:
        return (hoje, "fallback") if aceitar_sem_data else (None, None)
    return data_pub, "pubdate"


def _na_janela(pubdate: str, dias: int) -> bool:
    """
    True se a data de publicação está dentro da janela (últimos 'dias' dias).
    Sem pubDate → mantém (fallback). PubDate inválida → mantém.
    Descarta notícias antigas que o RSS retorna mesmo com when=7d (ex: 2017).
    """
    data_pub = _data_pubdate(pubdate)
    if data_pub is None:
        return True
    try:
        limite = (date.today() - timedelta(days=dias)).isoformat()
        return data_pub >= limite
    except Exception:
        return True


def search_news(query: str, regiao: str = REGIAO, max_resultados: int = 10, dias: int = 7) -> List[Dict]:
    """Busca menções via Google News RSS (últimos 'dias' dias) + DuckDuckGo Lite (fallback)."""
    resultados: List[Dict] = []

    # Tentativa 1: Google News RSS (with=7d limita aos últimos 7 dias)
    try:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(f"{query} {regiao}")
            + f"&when={dias}d"
            + "&hl=pt-BR&gl=BR"
        )
        xml = web_fetch(url, timeout=10)
        primeiro_termo = query.split()[0].lower()
        for r in parse_news_xml(xml):
            if primeiro_termo in r["titulo"].lower() or query.lower() in r["titulo"].lower():
                r["fonte"] = "google_news"
                resultados.append(r)
    except Exception:
        pass

    # Tentativa 2: DuckDuckGo Lite (fallback)
    if len(resultados) < 2:
        try:
            url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(f"{query} {regiao}")
            html = web_fetch(url, timeout=8)
            for link, title_html in re.findall(
                r'<a[^>]*href="([^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>',
                html, re.DOTALL,
            ):
                titulo = re.sub(r"<[^>]+>", "", title_html).strip()
                if titulo and len(titulo) > 10:
                    resultados.append({"titulo": titulo[:200], "url": link, "fonte": "duckduckgo"})
        except Exception:
            pass

    return resultados[:max_resultados]


def analisar_sentimento(texto: str) -> Dict:
    """Classifica sentimento por keyword matching. Retorna dict com classificação e percentuais."""
    texto_lower = texto.lower()
    pos = sum(1 for p in POSITIVO if p in texto_lower)
    neg = sum(1 for n in NEGATIVO if n in texto_lower)
    neu = sum(1 for n in NEUTRO if n in texto_lower)

    total = pos + neg + neu
    if total == 0:
        return {"classificacao": "neutro", "positivo": 33, "negativo": 33, "neutro": 34, "score": 0}

    pos_pct = round(pos / total * 100, 1)
    neg_pct = round(neg / total * 100, 1)
    neu_pct = round(neu / total * 100, 1)

    if pos > neg and pos > neu:
        classificacao = "positivo"
    elif neg > pos and neg > neu:
        classificacao = "negativo"
    else:
        classificacao = "neutro"

    return {
        "classificacao": classificacao,
        "positivo": pos_pct,
        "negativo": neg_pct,
        "neutro": neu_pct,
        "score": pos - neg,
    }


def _ler_config() -> Dict:
    """Lê scripts/config.json; retorna {} se indisponível (fallback p/ padrões)."""
    try:
        cfg_path = Path(__file__).parent / "config.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main() -> None:
    hoje = date.today().isoformat()
    config = _ler_config()
    termos = config.get("termos", TERMOS)
    max_resultados = int(config.get("max_resultados_por_termo", 10))
    janela_dias = int(config.get("janela_dias", 7))
    regiao = config.get("regiao", REGIAO)
    aceitar_sem_data = bool(config.get("aceitar_sem_data", False))

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, termo TEXT NOT NULL, titulo TEXT NOT NULL,
            url TEXT, fonte TEXT, sentimento TEXT, score INTEGER DEFAULT 0,
            boato_id INTEGER, created_at TEXT DEFAULT (datetime('now')),
            data_fonte TEXT
        )"""
    )
    # Migração: bancos antigos não têm data_fonte
    try:
        conn.execute("ALTER TABLE mencoes ADD COLUMN data_fonte TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mencoes_uniq ON mencoes(date, termo, titulo)"
    )

    resultados_gerais = []
    total_mencoes = 0
    descartados_sem_data = 0

    for termo in termos:
        try:
            mencoes = search_news(termo, regiao=regiao, max_resultados=max_resultados, dias=janela_dias)
        except Exception:
            mencoes = []

        # Dedup por título
        seen = set()
        unicas = []
        for m in mencoes:
            if m["titulo"] not in seen:
                seen.add(m["titulo"])
                unicas.append(m)

        # Sentimento por menção (não agregado por termo)
        for m in unicas:
            # Descarta notícias fora da janela (RSS às vezes retorna artigos antigos)
            if not _na_janela(m.get("pubdate", ""), janela_dias):
                continue

            # Sem pubDate válido: descarta (padrão) ou mantém marcado como fallback
            data_menção, data_fonte = _resolver_data(m.get("pubdate", ""), hoje, aceitar_sem_data)
            if data_menção is None:
                descartados_sem_data += 1
                continue

            sent = analisar_sentimento(m["titulo"])

            # Dedup global: se o título já foi captado (qualquer data/termo), pula
            cur_dedup = conn.cursor()
            cur_dedup.execute("SELECT id FROM mencoes WHERE titulo = ?", (m["titulo"],))
            if cur_dedup.fetchone():
                continue

            try:
                conn.execute(
                    """INSERT INTO mencoes (date, termo, titulo, url, fonte, sentimento, score, data_fonte)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(date, termo, titulo) DO UPDATE SET
                           url=excluded.url, fonte=excluded.fonte,
                           sentimento=excluded.sentimento, score=excluded.score""",
                    (data_menção, termo, m["titulo"], m.get("url", ""), m.get("fonte", ""),
                     sent["classificacao"], sent["score"], data_fonte),
                )
            except Exception as e:
                print(f"[coleta] erro ao gravar '{m['titulo'][:60]}': {e}", file=sys.stderr)

        # Resumo do termo (para o JSON de saída)
        sentimento_resumo = {"classificacao": "neutro", "positivo": 33, "negativo": 33, "neutro": 34, "score": 0}
        titulos_concatenados = " ".join(m["titulo"] for m in unicas)
        if titulos_concatenados:
            sentimento_resumo = analisar_sentimento(titulos_concatenados)

        total_mencoes += len(unicas)
        print(f"[coleta] {termo}: {len(unicas)} menções", file=sys.stderr)
        resultados_gerais.append({
            "termo": termo,
            "mencoes": len(unicas),
            "sentimento": sentimento_resumo,
            "titulos": [m["titulo"][:120] for m in unicas[:5]],
        })

    conn.commit()
    conn.close()

    output = {
        "status": "ok",
        "data": hoje,
        "regiao": regiao,
        "termos": len(termos),
        "mencoes": total_mencoes,
        "descartados_sem_data": descartados_sem_data,
        "resultados": resultados_gerais,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
