#!/bin/bash
# Cron 07:10 — gera relatório markdown de infodemia (stdout vira contexto do agente briefing)
# Default: últimos 7 dias (uso: bash cron_relatorio.sh [--dias N])
# DEPOIS de gerar, marca as notícias como exibidas (dedup para o próximo briefing).
# Localiza a raiz do projeto independente de onde o script for chamado
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD/scripts"

# Default da janela vem do config.json (janela_dias). Override opcional:
# bash cron_relatorio.sh --dias N
DIAS=""
if [ "$1" = "--dias" ] && [ -n "$2" ]; then
    DIAS="--dias $2"
fi

# 1. Gera o relatório (stdout = markdown com notícias novas)
python3 scripts/relatorio.py $DIAS 2>/dev/null

# 2. Marca as notícias do período como exibidas (dedup)
python3 scripts/marcar_exibidas.py $DIAS >/dev/null 2>&1
