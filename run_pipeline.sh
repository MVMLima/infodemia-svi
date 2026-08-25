#!/bin/bash
# Executa o pipeline completo de vigilância de infodemia:
#   init_db → coleta → análise → relatório
# Uso: bash run_pipeline.sh [--dias N]
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="$PWD/scripts"

DIAS=""
if [ "${1:-}" = "--dias" ] && [ -n "${2:-}" ]; then
    DIAS="--dias $2"
fi

echo "[1/4] init_db (schema SQLite)"
python3 scripts/init_db.py

echo "[2/4] coleta (Google News RSS + DuckDuckGo)"
python3 scripts/coleta.py

echo "[3/4] análise (picos z-score + classificação de boatos)"
python3 scripts/analise.py

echo "[4/4] relatório markdown"
python3 scripts/relatorio.py $DIAS
