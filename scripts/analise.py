import sqlite3
from datetime import datetime, timedelta
import statistics
from typing import Dict, List

from paths import db_path

DB_PATH = db_path()
# Garante que o diretório existe
from pathlib import Path
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Mínimo de dias com menção na janela de baseline para considerar pico
# (evita ALERTA falso em série esparsa — ex: 2 menções em 7 dias)
MIN_DIAS_BASELINE = 4

# Importa o matching de boatos real (módulo boatos.py)
from boatos import match_boato

def media_movel(conn: sqlite3.Connection, termo: str, date: str, janela: int = 7) -> float:
    """
    Calcula a média móvel do volume de menções para um termo nos últimos 'janela' dias.

    Dias sem menção contam como 0 (evita média inflada em série esparsa).
    """
    volumes = _volumes_janela(conn, termo, date, janela)
    if len(volumes) < 2:
        return 0.0
    return statistics.mean(volumes)


def desvio_padrao(conn: sqlite3.Connection, termo: str, date: str, janela: int = 7) -> float:
    """
    Calcula o desvio padrão do volume de menções para um termo nos últimos 'janela' dias.
    Dias sem menção contam como 0.
    """
    volumes = _volumes_janela(conn, termo, date, janela)
    if len(volumes) < 2:
        return 0.0
    return statistics.stdev(volumes)


def _volumes_janela(conn: sqlite3.Connection, termo: str, date: str, janela: int = 7) -> List[int]:
    """Volumes diários dos 'janela' dias anteriores a 'date' (exclusivo), zero quando sem menção."""
    data_ref = datetime.strptime(date, "%Y-%m-%d")
    datas = [(data_ref - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(1, janela + 1)]

    query = """
    SELECT date, COUNT(*) as volume
    FROM mencoes
    WHERE termo = ? AND date IN ({})
    GROUP BY date
    ORDER BY date
    """.format(", ".join(["?"] * len(datas)))

    cursor = conn.cursor()
    cursor.execute(query, [termo] + datas)
    volumes_por_dia = {row[0]: row[1] for row in cursor.fetchall()}

    # Preenche todos os dias da janela (dias sem menção = 0)
    return [volumes_por_dia.get(d, 0) for d in datas]

def detectar_picos(conn: sqlite3.Connection, date: str, janela: int = 7, limiar_z: float = 2.0) -> List[Dict[str, any]]:
    """
    Detecta picos de volume para termos com menções na data especificada.
    
    Args:
        conn: Conexão SQLite
        date: Data de referência (YYYY-MM-DD)
        janela: Janela para cálculo da média e desvio
        limiar_z: Limiar do Z-score para alerta (default: 2.0)
        
    Retorna:
        Lista de dicionários com informações sobre os picos detectados.
    """
    cursor = conn.cursor()
    picos = []
    
    # Termos com menções na data
    cursor.execute("""
    SELECT DISTINCT termo FROM mencoes WHERE date = ?
    """, [date])
    termos = [row[0] for row in cursor.fetchall()]
    
    for termo in termos:
        # Volume hoje
        cursor.execute("""
    SELECT COUNT(*) FROM mencoes WHERE termo = ? AND date = ?
    """, [termo, date])
        volume_hoje = cursor.fetchone()[0]
        
        # Média e desvio
        media = media_movel(conn, termo, date, janela)
        desvio = desvio_padrao(conn, termo, date, janela)

        # Sem baseline histórico (primeiros dias) não há pico detectável
        if media == 0 and desvio == 0:
            continue

        # Baseline insuficiente: exige mínimo de dias com menção na janela
        # (evita ALERTA em série esparsa — ex: 2 menções em 7 dias)
        dias_com_dado = sum(1 for v in _volumes_janela(conn, termo, date, janela) if v > 0)
        if dias_com_dado < MIN_DIAS_BASELINE:
            continue

        # Z-score
        if desvio == 0:
            if volume_hoje > media:
                zscore = 10.0  # Pico absoluto
            else:
                zscore = 0.0
        else:
            zscore = (volume_hoje - media) / desvio
        
        # Classificação
        acao = "ALERTA" if zscore >= limiar_z else "observacao" if volume_hoje > media else ""
        
        # Grava no banco
        cursor.execute("""
    INSERT INTO picos (date, termo, volume, media_7d, zscore, acao)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(date, termo) DO UPDATE SET
        volume=excluded.volume,
        media_7d=excluded.media_7d,
        zscore=excluded.zscore,
        acao=excluded.acao
    """, [date, termo, volume_hoje, media, zscore, acao])
        
        picos.append({
            "termo": termo,
            "volume": volume_hoje,
            "media_7d": media,
            "zscore": zscore,
            "acao": acao
        })
    
    return picos

def classificar_mencoes(conn: sqlite3.Connection, date: str) -> int:
    """
    Classifica menções como boatos (atualiza mencoes.boato_id e boatos_detectados).

    Menções de fact-checking/desmentido (ex: 'É #FAKE que...') são classificadas
    (boato_id preenchido para rastreabilidade) mas NÃO entram em boatos_detectados:
    elas são a resposta ao boato, não a propagação dele.
    """
    # Sinais de que a menção é um desmentido/fact-check, não propagação do boato
    SINAIS_CHECAGEM = [
        "#fake", "é fake", "e fake", "fato ou fake", "checagem", "desmentid",
        "notícia falsa", "noticia falsa", "é mentira", "e mentira",
        "não é verdade", "nao e verdade", "fake news",
    ]
    cursor = conn.cursor()
    count = 0

    # Menções não classificadas
    cursor.execute("""
    SELECT id, titulo, url, termo FROM mencoes WHERE date = ? AND boato_id IS NULL
    """, [date])
    mencoes = cursor.fetchall()

    for id_menção, titulo, url, termo in mencoes:
        boato = match_boato(titulo, conn=conn)
        if boato:
            # Obtém o ID do boato
            cursor.execute("""
            SELECT id FROM boatos WHERE slug = ?
            """, [boato["slug"]])
            boato_id = cursor.fetchone()

            if boato_id:
                boato_id = boato_id[0]
                # Atualiza a menção (sempre, mesmo fact-check)
                cursor.execute("""
                UPDATE mencoes SET boato_id = ? WHERE id = ?
                """, [boato_id, id_menção])

                # Fact-check/desmentido NÃO conta como propagação
                titulo_lower = titulo.lower()
                if any(s in titulo_lower for s in SINAIS_CHECAGEM):
                    continue

                # Verifica se já foi registrado hoje
                cursor.execute("""
                SELECT COUNT(*) FROM boatos_detectados 
                WHERE date = ? AND boato_id = ? AND titulo = ?
                """, [date, boato_id, titulo])
                if cursor.fetchone()[0] == 0:
                    # Registra novo boato detectado (com termo e url)
                    cursor.execute("""
                    INSERT INTO boatos_detectados (date, boato_id, termo, titulo, url)
                    VALUES (?, ?, ?, ?, ?)
                    """, [date, boato_id, termo, titulo, url])
                    count += 1

    return count

def _ler_config() -> Dict:
    """Lê scripts/config.json; retorna {} se indisponível."""
    try:
        import json
        cfg_path = Path(__file__).parent / "config.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    """
    CLI: analisa menções e detecta picos/boatos para os últimos N dias.

    Uso: python3 analise.py [--date YYYY-MM-DD] [--dias N]
    """
    import argparse
    import json

    config = _ler_config()
    limiar_z = float(config.get("limiar_zscore", 2.0))
    janela = int(config.get("janela_media", 7))

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Data de referência (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--dias", type=int, default=int(config.get("janela_dias", 7)), help="Quantos dias retroativos analisar (default do config.json)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    data_fim = datetime.strptime(args.date, "%Y-%m-%d").date()
    datas = [(data_fim - timedelta(days=i)).isoformat() for i in range(args.dias)]

    total_picos = []
    total_boatos = 0
    for d in datas:
        # Detecta picos
        picos = detectar_picos(conn, d, janela=janela, limiar_z=limiar_z)
        total_picos.extend(picos)
        # Classifica menções
        total_boatos += classificar_mencoes(conn, d)

    conn.commit()
    conn.close()

    print(json.dumps({
        "status": "ok",
        "data": args.date,
        "periodo": [datas[-1], datas[0]],
        "picos": total_picos,
        "boatos_detectados": total_boatos,
    }))

if __name__ == "__main__":
    main()