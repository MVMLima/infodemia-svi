import sqlite3
from pathlib import Path

from paths import db_path

DB_PATH = db_path()


def main():
    """Cria o banco de dados SQLite com o schema especificado."""
    # Garante que o diretório existe (efeito colateral só na execução, não na importação)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Cria as tabelas conforme o schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mencoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,              -- YYYY-MM-DD (data real da notícia/pubDate)
        termo TEXT NOT NULL,
        titulo TEXT NOT NULL,
        url TEXT,
        fonte TEXT,                      -- 'google_news' | 'duckduckgo'
        sentimento TEXT,                 -- 'positivo'/'negativo'/'neutro'
        score INTEGER DEFAULT 0,
        boato_id INTEGER,                -- FK para boatos.id se classificado, NULL caso contrário
        exibida INTEGER DEFAULT 0,       -- 1 = já apareceu em briefing anterior (dedup)
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mencoes_uniq ON mencoes(date, termo, titulo)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS boatos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        descricao TEXT,
        taticas TEXT,                    -- JSON list de strings
        keywords TEXT,                   -- JSON list de strings
        narrativa_substituta TEXT NOT NULL,
        fontes_oficiais TEXT,            -- JSON list de URLs
        status TEXT DEFAULT 'ativo'
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS picos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        termo TEXT NOT NULL,
        volume INTEGER NOT NULL,
        media_7d REAL,
        zscore REAL,
        acao TEXT,                       -- 'ALERTA' ou 'observacao'
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(date, termo)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS boatos_detectados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        boato_id INTEGER NOT NULL,
        termo TEXT,
        titulo TEXT,
        url TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migração: adiciona coluna exibida se o banco é antigo (dedup de briefing)
    try:
        cursor.execute("ALTER TABLE mencoes ADD COLUMN exibida INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    # Migração: origem da data da menção ('pubdate' | 'fallback') — auditoria
    try:
        cursor.execute("ALTER TABLE mencoes ADD COLUMN data_fonte TEXT")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    conn.commit()
    conn.close()
    print(f"Banco de dados criado/atualizado em {DB_PATH}")

if __name__ == "__main__":
    main()