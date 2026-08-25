#!/usr/bin/env python3
"""
relatorio.py — Relatório executivo de vigilância de infodemia (SVI-AC).

Gera relatório markdown com:
  - Resumo executivo (números prontos, sem o agente precisar somar)
  - Comparativo 7d vs 7d anteriores (tendência por termo)
  - Volume por termo (janela completa, com % negativa)
  - Série diária compacta (últimos 14 dias)
  - Notícias captadas (novas, exibida=0, com veículo real)
  - Picos detectados
  - Boatos detectados (últimos 7 dias; veículo em vez de URL gigante)
  - Veículos mais frequentes
  - Recomendações de ação
  - Nota metodológica

Uso: python3 relatorio.py [--date YYYY-MM-DD] [--dias N]
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from boatos import listar_boatos

from paths import db_path

DB_PATH = db_path()
CONFIG_PATH = Path(__file__).parent / "config.json"

# Janela de boatos exibidos no relatório: 7 dias (evita repetir boatos de 30 dias
# em todo briefing). Para decisão de [SILENT], o resumo mostra as últimas 48h.
JANELA_BOATOS = 7
JANELA_NOTICIAS_LIMITE = 25


def ler_config() -> Dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _boato_por_id(boatos: List[Dict]) -> Dict[int, Dict]:
    return {b["id"]: b for b in boatos}


def extrair_veiculo(titulo: str) -> str:
    """Extrai o veículo/domínio do título (após o último ' - '). Ex: '... - G1' → 'G1'."""
    if not titulo:
        return ""
    partes = titulo.rsplit(" - ", 1)
    if len(partes) == 2 and 0 < len(partes[1].strip()) <= 40:
        return partes[1].strip()
    return ""


def dominio_url(url: str) -> str:
    """Extrai o domínio de uma URL (fallback quando o título não tem veículo)."""
    if not url:
        return ""
    host = urlparse(url).netloc
    host = host.replace("www.", "")
    return host[:40] or ""


def _veiculo_menção(titulo: str, url: str) -> str:
    return extrair_veiculo(titulo) or dominio_url(url) or "—"


def _resumo_executivo(
    conn: sqlite3.Connection, ini_str: str, fim_str: str, data_fim: date
) -> List[str]:
    """Bloco de números prontos: totais, % negativa, top termos, 48h."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*), "
        "SUM(CASE WHEN sentimento='negativo' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN sentimento='positivo' THEN 1 ELSE 0 END) "
        "FROM mencoes WHERE date BETWEEN ? AND ?",
        (ini_str, fim_str),
    )
    total, neg, pos = cur.fetchone()
    total, neg, pos = total or 0, neg or 0, pos or 0
    pct_neg = round(neg / total * 100) if total else 0

    # Últimos 7 dias (para decisão de [SILENT] e foco do briefing)
    d7 = data_fim - timedelta(days=6)
    cur.execute(
        "SELECT COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ?",
        (d7.isoformat(), fim_str),
    )
    total_7d = cur.fetchone()[0] or 0

    # Top 3 termos (últimos 7 dias)
    cur.execute(
        "SELECT termo, COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ? "
        "GROUP BY termo ORDER BY COUNT(*) DESC LIMIT 3",
        (d7.isoformat(), fim_str),
    )
    top = ", ".join(f"`{t}` ({n})" for t, n in cur.fetchall()) or "—"

    # Novidades nas últimas 48h (base para o agente decidir [SILENT])
    d48 = data_fim - timedelta(days=1)  # hoje + ontem
    cur.execute(
        "SELECT COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ? AND exibida = 0",
        (d48.isoformat(), fim_str),
    )
    novas_48h = cur.fetchone()[0] or 0
    cur.execute(
        "SELECT COUNT(DISTINCT boato_id) FROM boatos_detectados WHERE date BETWEEN ? AND ?",
        (d48.isoformat(), fim_str),
    )
    boatos_48h = cur.fetchone()[0] or 0
    cur.execute(
        "SELECT COUNT(*) FROM picos WHERE date BETWEEN ? AND ? AND acao = 'ALERTA'",
        (d48.isoformat(), fim_str),
    )
    picos_48h = cur.fetchone()[0] or 0

    linhas = [
        f"- **Menções (janela):** {total} | **Últimos 7d:** {total_7d}",
        f"- **Negativas:** {neg} ({pct_neg}%) | **Positivas:** {pos}",
        f"- **Top termos (7d):** {top}",
        f"- **Novidades 48h:** {novas_48h} notícia(s) nova(s), {boatos_48h} boato(s), {picos_48h} alerta(s) de pico",
    ]
    return linhas


def _comparativo(conn: sqlite3.Connection, data_fim: date, dias: int = 7) -> List[Tuple]:
    """Menções por termo: período atual vs período anterior equivalente (Δ e %)."""
    cur = conn.cursor()
    ini_atual = (data_fim - timedelta(days=dias - 1)).isoformat()
    fim_ant = (data_fim - timedelta(days=dias)).isoformat()
    ini_ant = (data_fim - timedelta(days=2 * dias - 1)).isoformat()

    cur.execute(
        "SELECT termo, COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ? GROUP BY termo",
        (ini_atual, data_fim.isoformat()),
    )
    atual = dict(cur.fetchall())
    cur.execute(
        "SELECT termo, COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ? GROUP BY termo",
        (ini_ant, fim_ant),
    )
    anterior = dict(cur.fetchall())

    linhas = []
    for termo in sorted(set(atual) | set(anterior), key=lambda t: atual.get(t, 0), reverse=True):
        a = atual.get(termo, 0)
        b = anterior.get(termo, 0)
        if b == 0:
            var: Optional[int] = None if a == 0 else 999  # 999 = termo novo no período
        else:
            var = round((a - b) / b * 100)
        linhas.append((termo, a, b, a - b, var))
    return linhas


def _serie_diaria(conn: sqlite3.Connection, data_fim: date, dias: int = 14) -> List[str]:
    """Menções por dia (compacto) dos últimos 'dias' dias."""
    cur = conn.cursor()
    ini = (data_fim - timedelta(days=dias - 1)).isoformat()
    cur.execute(
        "SELECT date, COUNT(*) FROM mencoes WHERE date BETWEEN ? AND ? GROUP BY date",
        (ini, data_fim.isoformat()),
    )
    vol = dict(cur.fetchall())
    return [
        f"{d.strftime('%d/%m')}:{vol.get(d.isoformat(), 0)}"
        for d in ((data_fim - timedelta(days=i)) for i in range(dias - 1, -1, -1))
    ]


def _top_veiculos(conn: sqlite3.Connection, ini_str: str, fim_str: str, limite: int = 5) -> List[Tuple[str, int]]:
    """Veículos mais frequentes no período (do título ou domínio da URL)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT titulo, url FROM mencoes WHERE date BETWEEN ? AND ?", (ini_str, fim_str)
    )
    contagem: Dict[str, int] = {}
    for titulo, url in cur.fetchall():
        v = _veiculo_menção(titulo, url)
        contagem[v] = contagem.get(v, 0) + 1
    return sorted(contagem.items(), key=lambda x: -x[1])[:limite]


def gerar_relatorio(conn: sqlite3.Connection, data_ref: str, dias: int = 1) -> str:
    """Gera o relatório markdown para o período (data_ref - dias + 1 até data_ref)."""
    config = ler_config()
    data_fim = date.fromisoformat(data_ref)
    data_ini = data_fim - timedelta(days=dias - 1)
    ini_str, fim_str = data_ini.isoformat(), data_fim.isoformat()

    boatos = listar_boatos(conn)
    boatos_by_id = _boato_por_id(boatos)

    # --- Volume por termo (janela completa) ---
    cursor = conn.cursor()
    cursor.execute(
        """SELECT termo, COUNT(*), 
                  SUM(CASE WHEN sentimento='negativo' THEN 1 ELSE 0 END) AS neg,
                  SUM(CASE WHEN sentimento='positivo' THEN 1 ELSE 0 END) AS pos
           FROM mencoes WHERE date BETWEEN ? AND ? GROUP BY termo ORDER BY COUNT(*) DESC""",
        (ini_str, fim_str),
    )
    vol_termo = cursor.fetchall()

    # --- Picos ---
    cursor.execute(
        """SELECT termo, volume, media_7d, zscore, acao FROM picos
           WHERE date BETWEEN ? AND ? ORDER BY zscore DESC""",
        (ini_str, fim_str),
    )
    picos = cursor.fetchall()

    # --- Notícias captadas (novas, ainda não exibidas em briefing) ---
    cursor.execute(
        """SELECT date, termo, titulo, url, fonte, sentimento
           FROM mencoes
           WHERE date BETWEEN ? AND ? AND exibida = 0
           ORDER BY date DESC, id DESC
           LIMIT ?""",
        (ini_str, fim_str, JANELA_NOTICIAS_LIMITE + 1),
    )
    noticias_novas = cursor.fetchall()
    noticias_extra = len(noticias_novas) - JANELA_NOTICIAS_LIMITE
    if noticias_extra > 0:
        noticias_novas = noticias_novas[:JANELA_NOTICIAS_LIMITE]
    else:
        noticias_extra = 0

    # --- Boatos detectados (últimos 7 dias; veículo em vez de URL gigante) ---
    b_ini = data_fim - timedelta(days=JANELA_BOATOS - 1)
    cursor.execute(
        """SELECT bd.date, bd.boato_id, bd.titulo, bd.url
           FROM boatos_detectados bd
           WHERE bd.date BETWEEN ? AND ? ORDER BY bd.date DESC, bd.boato_id""",
        (b_ini.isoformat(), fim_str),
    )
    boatos_det = cursor.fetchall()

    # Agrupa menções por boato_id, mantendo ordem de ocorrência
    boatos_agrupados: Dict[int, list] = {}
    for det_date, boato_id, titulo, url in boatos_det:
        boatos_agrupados.setdefault(boato_id, []).append((det_date, titulo, url))

    linhas: List[str] = []
    linhas.append(f"# Relatório de Vigilância de Infodemia — {config.get('regiao', 'Acre')}")
    linhas.append("")
    linhas.append(f"**Período:** {ini_str} a {fim_str}  ")
    linhas.append(f"**Gerado em:** {date.today().isoformat()}  ")
    linhas.append(f"**Comparativo 7d:** {data_fim - timedelta(days=13):%d/%m} a {data_fim - timedelta(days=7):%d/%m} (anterior)")
    linhas.append("")

    # Resumo executivo (números prontos)
    linhas.append("## Resumo executivo")
    linhas.append("")
    linhas.extend(_resumo_executivo(conn, ini_str, fim_str, data_fim))
    linhas.append("")

    # Comparativo 7d vs 7d anteriores
    linhas.append("## Comparativo (últimos 7d vs 7d anteriores)")
    linhas.append("")
    comp = _comparativo(conn, data_fim, dias=7)
    if comp:
        linhas.append("| Termo | 7d | 7d ant. | Δ | Var % |")
        linhas.append("|-------|----:|--------:|----:|------:|")
        for termo, a, b, delta, var in comp:
            if var is None:
                var_str = "—"
            elif var == 999:
                var_str = "novo"
            else:
                seta = "↑" if var >= 50 else ("↓" if var <= -33 else "→")
                var_str = f"{seta} {var:+d}%"
            linhas.append(f"| {termo} | {a} | {b} | {delta:+d} | {var_str} |")
    else:
        linhas.append("_Sem menções nos períodos comparados._")
    linhas.append("")

    # Termos monitorados
    linhas.append("## Termos monitorados")
    linhas.append("")
    linhas.append(", ".join(f"`{t}`" for t in config.get("termos", [])))
    linhas.append("")

    # Volume por termo (janela completa, com % negativa)
    linhas.append("## Volume por termo")
    linhas.append("")
    if vol_termo:
        linhas.append("| Termo | Menções | Negativas | Neg % | Positivas |")
        linhas.append("|-------|--------:|----------:|------:|----------:|")
        for termo, total, neg, pos in vol_termo:
            pct = round(neg / total * 100) if total else 0
            linhas.append(f"| {termo} | {total} | {neg} | {pct}% | {pos} |")
    else:
        linhas.append("_Nenhuma menção no período._")
    linhas.append("")

    # Série diária compacta
    linhas.append("## Menções por dia (últimos 14 dias)")
    linhas.append("")
    linhas.append("`" + "  ".join(_serie_diaria(conn, data_fim)) + "`")
    linhas.append("")

    # Notícias captadas (novas)
    linhas.append("## Notícias captadas")
    linhas.append("")
    if noticias_novas:
        n_total = len(noticias_novas) + noticias_extra
        linhas.append(f"_{n_total} notícia(s) nova(s) no período._")
        linhas.append("")
        linhas.append("| Data | Termo | Notícia | Veículo | Sentimento |")
        linhas.append("|------|-------|---------|---------|------------|")
        for det_date, termo, titulo, url, fonte, sentimento in noticias_novas:
            titulo_curto = titulo[:80] + ("…" if len(titulo) > 80 else "")
            link = f"[{titulo_curto}]({url})" if url else titulo_curto
            linhas.append(f"| {det_date} | {termo} | {link} | {_veiculo_menção(titulo, url)} | {sentimento or '-'} |")
        if noticias_extra:
            linhas.append("")
            linhas.append(f"_…e mais {noticias_extra} notícia(s) — ver banco para a lista completa._")
        linhas.append("")
    else:
        linhas.append("_Nenhuma notícia nova no período (todas já exibidas em briefings anteriores)._")
        linhas.append("")

    # Picos
    linhas.append("## Picos detectados")
    linhas.append("")
    if picos:
        linhas.append("| Termo | Volume | Média 7d | Z-score | Ação |")
        linhas.append("|-------|-------:|---------:|--------:|------|")
        for termo, volume, media, zscore, acao in picos:
            linhas.append(f"| {termo} | {volume} | {media:.1f} | {zscore:.2f} | {acao} |")
    else:
        linhas.append("_Nenhum pico no período._")
    linhas.append("")

    # Boatos detectados
    linhas.append("## Boatos detectados")
    linhas.append("")
    if boatos_agrupados:
        linhas.append(f"_(últimos {JANELA_BOATOS} dias; só os com menção no período)_")
        linhas.append("")
        for boato_id, mencoes in boatos_agrupados.items():
            b = boatos_by_id.get(boato_id)
            if not b:
                continue
            linhas.append(f"### {b['nome']} _(N={len(mencoes)} menção(ões))_")
            linhas.append("")
            linhas.append(f"**Táticas usadas:** {', '.join(b['taticas'])}")
            linhas.append("")
            linhas.append("**Menções que dispararam:**")
            for det_date, titulo, url in mencoes:
                linhas.append(f"- ({det_date}) {titulo} — {_veiculo_menção(titulo, url)}")
            linhas.append("")
            linhas.append("> **Narrativa substituta pronta para resposta:**")
            linhas.append(f"> {b['narrativa_substituta']}")
            linhas.append("")
            if b["fontes_oficiais"]:
                linhas.append("**Fontes oficiais:** " + ", ".join(b["fontes_oficiais"]))
            linhas.append("")
    else:
        linhas.append("_Nenhum boato detectado nos últimos 7 dias._")
    linhas.append("")

    # Veículos mais frequentes
    linhas.append("## Veículos mais frequentes")
    linhas.append("")
    top_v = _top_veiculos(conn, ini_str, fim_str)
    if top_v:
        linhas.append("| Veículo | Menções |")
        linhas.append("|---------|--------:|")
        for veiculo, n in top_v:
            linhas.append(f"| {veiculo} | {n} |")
    else:
        linhas.append("_Sem menções no período._")
    linhas.append("")

    # Recomendações
    linhas.append("## Recomendações de resposta")
    linhas.append("")
    if boatos_agrupados:
        # Táticas distintas dos boatos detectados no período
        taticas_uso = sorted({
            t
            for boato_id in boatos_agrupados
            for t in (boatos_by_id.get(boato_id) or {}).get("taticas", [])
        })
        linhas.append("- Divulgar nota oficial com as narrativas substitutas prontas acima.")
        linhas.append("- **Prebunking:** lançar campanha ensinando as táticas usadas")
        if taticas_uso:
            linhas.append("  (" + ", ".join(taticas_uso) + ").")
        else:
            linhas.append("  (reconhecimento de padrões de desinformação).")
        linhas.append("- Acionar canais oficiais de checagem e perfis locais de confiança")
        linhas.append("  (agentes comunitários, lideranças locais) para amplificar a resposta.")
        linhas.append("- Monitorar os termos de maior volume nos próximos 7 dias.")
    else:
        linhas.append("- Nenhuma ação imediata; manter monitoramento diário.")
        linhas.append("- Reforçar comunicação de rotina sobre vacinação (normalização do estrutural).")
    linhas.append("")

    # Nota metodológica
    linhas.append("## Nota metodológica")
    linhas.append("")
    linhas.append("- **Fontes:** Google News RSS + DuckDuckGo Lite (menções públicas de notícias/web).")
    linhas.append("- **Análise:** sentimento por keyword matching; detecção de pico por z-score")
    linhas.append("  vs. média móvel de 7 dias; classificação de boatos por base de conhecimento.")
    linhas.append("- **Limitação:** não é amostra completa das redes sociais; reflete menções")
    linhas.append("  públicas indexadas. Picos de WhatsApp/grupos fechados não são capturados.")
    linhas.append("")

    return "\n".join(linhas)


def main() -> None:
    config = ler_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="Data final do período (YYYY-MM-DD)")
    parser.add_argument("--dias", type=int, default=int(config.get("janela_dias", 7)), help="Nº de dias do período (default do config.json)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    print(f"[relatorio] gerando relatório até {args.date} ({args.dias} dia(s))", file=sys.stderr)
    rel = gerar_relatorio(conn, args.date, args.dias)
    conn.close()
    print(rel)


if __name__ == "__main__":
    main()
